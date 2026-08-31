import json
import urllib.parse
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.payment import PaymentConfiguration, DepositRequest, WithdrawalRequest
from app.models.risk_audit import AuditLog, RiskFlag
from app.schemas.economics import EconomicsPreviewResponse
from app.schemas.risk_audit import RiskFlagResponse, RiskFlagResolveRequest, AuditLogResponse
from app.schemas.payment import PaymentConfigResponse, PaymentConfigUpdate
from app.schemas.game import AviatorConfigUpdate
from app.schemas.user import UserResponse, VerifierCreateRequest
from app.api.deps import require_roles, get_password_hash
from app.services.economics_service import EconomicsService
from app.services.risk_service import RiskService
from app.services.payment_service import PaymentService
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/admin", tags=["Admin Analytics & Financial Desk"])

@router.get("/economics/preview", response_model=EconomicsPreviewResponse)
def get_economics_preview(
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    return EconomicsService.get_economics_preview(db)

@router.get("/risk-flags", response_model=List[RiskFlagResponse])
def get_risk_flags(
    status: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.PAYMENT_VERIFIER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    flags = RiskService.list_flags(db, status_filter=status)
    return flags

@router.post("/risk-flags/{flag_id}/resolve", response_model=RiskFlagResponse)
def resolve_risk_flag(
    flag_id: int,
    req: RiskFlagResolveRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    return RiskService.update_flag_status(db, flag_id, req.status.value)

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs

# Payment Verifier Management (Super Admin)
@router.get("/verifiers", response_model=List[UserResponse])
def list_payment_verifiers(
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    verifiers = db.query(User).filter(User.role == UserRole.PAYMENT_VERIFIER.value).order_by(User.created_at.desc()).all()
    return verifiers

@router.post("/verifiers", response_model=UserResponse)
def create_payment_verifier(
    req: VerifierCreateRequest,
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(
        (User.username == req.username.strip()) | (User.email == req.email.strip())
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username or email already exists."
        )

    verifier = User(
        username=req.username.strip(),
        email=req.email.strip(),
        hashed_password=get_password_hash(req.password),
        role=UserRole.PAYMENT_VERIFIER.value,
        is_active=True,
        is_verified=True
    )
    db.add(verifier)
    db.flush()

    WalletService.get_or_create_wallet(db, verifier.id)

    audit = AuditLog(
        admin_id=current_user.id,
        action="CREATE_PAYMENT_VERIFIER",
        target_type="User",
        target_id=str(verifier.id),
        changes=json.dumps({"username": verifier.username, "email": verifier.email})
    )
    db.add(audit)
    db.commit()
    db.refresh(verifier)
    return verifier

@router.delete("/verifiers/{verifier_id}")
def delete_payment_verifier(
    verifier_id: int,
    current_user: User = Depends(require_roles([UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    verifier = db.query(User).filter(User.id == verifier_id).first()
    if not verifier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verifier not found.")
    if verifier.role != UserRole.PAYMENT_VERIFIER.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target user is not a Payment Verifier.")

    username = verifier.username

    # Nullify references in deposit & withdrawal requests to maintain data integrity
    db.query(DepositRequest).filter(DepositRequest.verified_by_id == verifier_id).update({"verified_by_id": None})
    db.query(WithdrawalRequest).filter(WithdrawalRequest.processed_by_id == verifier_id).update({"processed_by_id": None})

    audit = AuditLog(
        admin_id=current_user.id,
        action="DELETE_PAYMENT_VERIFIER",
        target_type="User",
        target_id=str(verifier_id),
        changes=json.dumps({"username": username, "email": verifier.email})
    )
    db.add(audit)
    db.delete(verifier)
    db.commit()
    return {"message": f"Payment verifier '{username}' deleted successfully."}

def _serialize_payment_config(config: PaymentConfiguration) -> dict:
    qr_url = config.qr_code_url
    if not qr_url:
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi%3A%2F%2Fpay%3Fpa%3D{urllib.parse.quote(config.upi_id)}%26pn%3DAURA%2520GAMING%26cu%3DINR"

    return {
        "id": config.id,
        "upi_id": config.upi_id,
        "qr_code_url": qr_url,
        "min_deposit": config.min_deposit,
        "max_deposit": config.max_deposit,
        "min_withdrawal": config.min_withdrawal,
        "max_withdrawal": config.max_withdrawal,
        "min_deposit_inr": config.min_deposit / 100.0,
        "max_deposit_inr": config.max_deposit / 100.0,
        "min_withdrawal_inr": config.min_withdrawal / 100.0,
        "max_withdrawal_inr": config.max_withdrawal / 100.0,
        "is_active": config.is_active,
        "updated_at": config.updated_at
    }

@router.get("/payment-config", response_model=PaymentConfigResponse)
def get_payment_config(
    current_user: User = Depends(require_roles([UserRole.PAYMENT_VERIFIER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    config = PaymentService.get_or_create_config(db)
    return _serialize_payment_config(config)

@router.put("/payment-config", response_model=PaymentConfigResponse)
def update_payment_config(
    req: PaymentConfigUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    config = PaymentService.get_or_create_config(db)

    if req.upi_id is not None:
        clean_upi = req.upi_id.strip()
        if clean_upi:
            config.upi_id = clean_upi
            if req.qr_code_url is None:
                config.qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi%3A%2F%2Fpay%3Fpa%3D{urllib.parse.quote(clean_upi)}%26pn%3DAURA%2520GAMING%26cu%3DINR"

    if req.qr_code_url is not None:
        config.qr_code_url = req.qr_code_url

    if req.min_deposit_inr is not None:
        config.min_deposit = int(round(req.min_deposit_inr * 100))
    elif req.min_deposit is not None:
        config.min_deposit = req.min_deposit

    if req.max_deposit_inr is not None:
        config.max_deposit = int(round(req.max_deposit_inr * 100))
    elif req.max_deposit is not None:
        config.max_deposit = req.max_deposit

    if req.min_withdrawal_inr is not None:
        config.min_withdrawal = int(round(req.min_withdrawal_inr * 100))
    elif req.min_withdrawal is not None:
        config.min_withdrawal = req.min_withdrawal

    if req.max_withdrawal_inr is not None:
        config.max_withdrawal = int(round(req.max_withdrawal_inr * 100))
    elif req.max_withdrawal is not None:
        config.max_withdrawal = req.max_withdrawal

    if req.is_active is not None:
        config.is_active = req.is_active

    config.updated_by_id = current_user.id

    audit = AuditLog(
        admin_id=current_user.id,
        action="UPDATE_PAYMENT_CONFIG",
        target_type="PaymentConfiguration",
        target_id=str(config.id),
        changes=json.dumps({
            "upi_id": config.upi_id,
            "min_deposit": config.min_deposit,
            "max_deposit": config.max_deposit,
            "min_withdrawal": config.min_withdrawal,
            "max_withdrawal": config.max_withdrawal
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(config)
    return _serialize_payment_config(config)

@router.get("/aviator-config")
def get_aviator_config(
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    from app.services.crash_manager import CrashRoundManager
    from app.models.game import Game, GameCode
    mgr = CrashRoundManager.get_instance()
    game = db.query(Game).filter(Game.code == GameCode.CRASH.value).first()

    min_bet_inr = (game.min_bet / 100.0) if game else 10.0
    max_bet_inr = (game.max_bet / 100.0) if game else 50000.0

    return {
        "min_crash_multiplier": mgr.min_crash_multiplier,
        "max_crash_multiplier": mgr.max_crash_multiplier,
        "min_bet_inr": min_bet_inr,
        "max_bet_inr": max_bet_inr
    }

@router.put("/aviator-config")
def update_aviator_config(
    req: AviatorConfigUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    from app.services.crash_manager import CrashRoundManager
    from app.models.game import Game, GameCode
    mgr = CrashRoundManager.get_instance()
    try:
        mgr.update_limits(req.min_crash_multiplier, req.max_crash_multiplier)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    game = db.query(Game).filter(Game.code == GameCode.CRASH.value).first()
    if game:
        if req.min_bet_inr is not None:
            if req.min_bet_inr < 1.0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Minimum bet amount must be at least ₹1.00")
            game.min_bet = int(round(req.min_bet_inr * 100))

        if req.max_bet_inr is not None:
            if req.max_bet_inr < (game.min_bet / 100.0):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum bet amount must be greater than Minimum bet amount")
            game.max_bet = int(round(req.max_bet_inr * 100))

        db.commit()
        db.refresh(game)

    min_bet_inr = (game.min_bet / 100.0) if game else 10.0
    max_bet_inr = (game.max_bet / 100.0) if game else 50000.0

    audit = AuditLog(
        admin_id=current_user.id,
        action="UPDATE_AVIATOR_LIMITS",
        target_type="Game",
        target_id="CRASH",
        changes=json.dumps({
            "min_crash_multiplier": mgr.min_crash_multiplier,
            "max_crash_multiplier": mgr.max_crash_multiplier,
            "min_bet_inr": min_bet_inr,
            "max_bet_inr": max_bet_inr
        })
    )
    db.add(audit)
    db.commit()

    return {
        "message": f"Aviator limits updated: Multipliers ({mgr.min_crash_multiplier:.2f}x - {mgr.max_crash_multiplier:.2f}x) | Bet Range (₹{min_bet_inr:.2f} - ₹{max_bet_inr:.2f})",
        "min_crash_multiplier": mgr.min_crash_multiplier,
        "max_crash_multiplier": mgr.max_crash_multiplier,
        "min_bet_inr": min_bet_inr,
        "max_bet_inr": max_bet_inr
    }

