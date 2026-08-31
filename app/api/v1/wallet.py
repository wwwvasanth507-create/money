import urllib.parse
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.wallet import WalletResponse, WalletTransactionResponse
from app.schemas.payment import DepositResponse, WithdrawalResponse, WithdrawalCreateRequest, PaymentConfigResponse
from app.api.deps import get_current_user
from app.services.wallet_service import WalletService
from app.services.payment_service import PaymentService
from app.services.kyc_service import KYCService
from app.services.responsible_gaming_service import ResponsibleGamingService
from app.models.wallet import WalletTransaction, Wallet

router = APIRouter(prefix="/wallet", tags=["Wallet & Payments"])

@router.get("/config", response_model=PaymentConfigResponse)
def get_wallet_payment_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = PaymentService.get_or_create_config(db)
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

@router.get("/balance", response_model=WalletResponse)
def get_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = WalletService.get_or_create_wallet(db, current_user.id)
    return {
        "id": wallet.id,
        "user_id": wallet.user_id,
        "real_balance": wallet.real_balance,
        "bonus_balance": wallet.bonus_balance,
        "locked_balance": wallet.locked_balance,
        "available_balance": wallet.available_balance,
        "real_balance_inr": wallet.real_balance / 100.0,
        "available_balance_inr": wallet.available_balance / 100.0,
        "currency": wallet.currency
    }


@router.get("/transactions", response_model=List[WalletTransactionResponse])
def get_transactions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet = WalletService.get_or_create_wallet(db, current_user.id)
    txs = db.query(WalletTransaction).filter(
        WalletTransaction.wallet_id == wallet.id
    ).order_by(WalletTransaction.created_at.desc()).limit(limit).all()

    return [
        {
            "id": tx.id,
            "transaction_id": tx.transaction_id,
            "user_id": tx.user_id,
            "type": tx.type,
            "amount": tx.amount,
            "amount_inr": tx.amount / 100.0,
            "balance_before": tx.balance_before,
            "balance_after": tx.balance_after,
            "reference_id": tx.reference_id,
            "reference_type": tx.reference_type,
            "status": tx.status,
            "created_by": tx.created_by,
            "description": tx.description,
            "created_at": tx.created_at
        }
        for tx in txs
    ]

@router.post("/deposit", response_model=DepositResponse)
def submit_deposit(
    utr_number: str = Form(...),
    amount_inr: float = Form(...),
    proof_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check self exclusion
    ResponsibleGamingService.check_self_exclusion(db, current_user.id)

    amount_paise = int(round(amount_inr * 100))

    # Check deposit limits
    ResponsibleGamingService.validate_deposit_limits(db, current_user.id, amount_paise)

    proof_path = None
    if proof_file and proof_file.filename:
        proof_path = KYCService.validate_and_save_image(proof_file, current_user.id, "deposit_proof")

    deposit_req = PaymentService.submit_deposit(
        db=db,
        user_id=current_user.id,
        utr_number=utr_number,
        amount_paise=amount_paise,
        proof_image_path=proof_path
    )

    return {
        "id": deposit_req.id,
        "user_id": deposit_req.user_id,
        "utr_number": deposit_req.utr_number,
        "amount": deposit_req.amount,
        "amount_inr": deposit_req.amount / 100.0,
        "payment_method": deposit_req.payment_method,
        "proof_image_path": deposit_req.proof_image_path,
        "status": deposit_req.status,
        "verifier_notes": deposit_req.verifier_notes,
        "verified_by_id": deposit_req.verified_by_id,
        "verified_at": deposit_req.verified_at,
        "created_at": deposit_req.created_at
    }

@router.post("/withdraw", response_model=WithdrawalResponse)
def submit_withdrawal(
    req: WithdrawalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ResponsibleGamingService.check_self_exclusion(db, current_user.id)

    withdrawal_req = PaymentService.submit_withdrawal(
        db=db,
        user_id=current_user.id,
        amount_paise=req.amount,
        bank_account_number=req.bank_account_number,
        ifsc_code=req.ifsc_code,
        account_holder_name=req.account_holder_name,
        upi_id=req.upi_id
    )

    return {
        "id": withdrawal_req.id,
        "user_id": withdrawal_req.user_id,
        "amount": withdrawal_req.amount,
        "amount_inr": withdrawal_req.amount / 100.0,
        "bank_account_number": withdrawal_req.bank_account_number,
        "ifsc_code": withdrawal_req.ifsc_code,
        "account_holder_name": withdrawal_req.account_holder_name,
        "upi_id": withdrawal_req.upi_id,
        "status": withdrawal_req.status,
        "notes": withdrawal_req.notes,
        "processed_by_id": withdrawal_req.processed_by_id,
        "processed_at": withdrawal_req.processed_at,
        "created_at": withdrawal_req.created_at
    }

@router.get("/deposit-claims")
def get_user_deposit_claims(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.payment import DepositRequest
    claims = db.query(DepositRequest).filter(
        DepositRequest.user_id == current_user.id
    ).order_by(DepositRequest.created_at.desc()).limit(20).all()

    res = []
    for c in claims:
        if c.status == "PENDING":
            msg = "please wait your amount is credited after the verification"
        elif c.status == "APPROVED":
            msg = "completed"
        elif c.status == "REJECTED":
            msg = "failed"
        else:
            msg = c.status

        res.append({
            "id": c.id,
            "utr_number": c.utr_number,
            "amount_inr": c.amount / 100.0,
            "payment_method": c.payment_method,
            "status": c.status,
            "status_message": msg,
            "verifier_notes": c.verifier_notes,
            "created_at": c.created_at
        })
    return res

@router.get("/withdrawal-claims")
def get_user_withdrawal_claims(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.payment import WithdrawalRequest
    claims = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.user_id == current_user.id
    ).order_by(WithdrawalRequest.created_at.desc()).limit(20).all()

    res = []
    for w in claims:
        if w.status == "PENDING":
            msg = "withdrawal amount is deposited in your account within 3 working days"
        elif w.status == "APPROVED":
            msg = "completed"
        elif w.status == "REJECTED":
            msg = "failed"
        else:
            msg = w.status

        res.append({
            "id": w.id,
            "amount_inr": w.amount / 100.0,
            "upi_id": w.upi_id,
            "bank_account_number": w.bank_account_number,
            "ifsc_code": w.ifsc_code,
            "account_holder_name": w.account_holder_name,
            "status": w.status,
            "status_message": msg,
            "notes": w.notes,
            "created_at": w.created_at
        })
    return res

