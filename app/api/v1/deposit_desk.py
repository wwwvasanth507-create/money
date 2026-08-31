from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.payment import DepositRequest, WithdrawalRequest, DepositStatus, WithdrawalStatus
from app.schemas.payment import DepositResponse, DepositVerifyRequest, WithdrawalResponse, WithdrawalProcessRequest
from app.api.deps import require_roles
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/admin", tags=["Payment Verification Desk & Admin Operations"])

@router.get("/deposits/pending", response_model=List[DepositResponse])
def get_pending_deposits(
    current_user: User = Depends(require_roles([UserRole.PAYMENT_VERIFIER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    deposits = db.query(DepositRequest).filter(
        DepositRequest.status.in_([DepositStatus.PENDING.value, DepositStatus.INFO_REQUESTED.value])
    ).order_by(DepositRequest.created_at.asc()).all()

    return [
        {
            "id": d.id,
            "user_id": d.user_id,
            "utr_number": d.utr_number,
            "amount": d.amount,
            "amount_inr": d.amount / 100.0,
            "payment_method": d.payment_method,
            "proof_image_path": d.proof_image_path,
            "status": d.status,
            "verifier_notes": d.verifier_notes,
            "verified_by_id": d.verified_by_id,
            "verified_at": d.verified_at,
            "created_at": d.created_at
        }
        for d in deposits
    ]

@router.post("/deposits/{deposit_id}/verify", response_model=DepositResponse)
def verify_deposit_claim(
    deposit_id: int,
    req: DepositVerifyRequest,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.PAYMENT_VERIFIER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    d = PaymentService.verify_deposit(
        db=db,
        deposit_id=deposit_id,
        verifier_user=current_user,
        action=req.action,
        verifier_notes=req.verifier_notes,
        ip_address=client_ip
    )

    return {
        "id": d.id,
        "user_id": d.user_id,
        "utr_number": d.utr_number,
        "amount": d.amount,
        "amount_inr": d.amount / 100.0,
        "payment_method": d.payment_method,
        "proof_image_path": d.proof_image_path,
        "status": d.status,
        "verifier_notes": d.verifier_notes,
        "verified_by_id": d.verified_by_id,
        "verified_at": d.verified_at,
        "created_at": d.created_at
    }

@router.get("/withdrawals/pending", response_model=List[WithdrawalResponse])
def get_pending_withdrawals(
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    withdrawals = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.status == WithdrawalStatus.PENDING.value
    ).order_by(WithdrawalRequest.created_at.asc()).all()

    return [
        {
            "id": w.id,
            "user_id": w.user_id,
            "amount": w.amount,
            "amount_inr": w.amount / 100.0,
            "bank_account_number": w.bank_account_number,
            "ifsc_code": w.ifsc_code,
            "account_holder_name": w.account_holder_name,
            "upi_id": w.upi_id,
            "status": w.status,
            "notes": w.notes,
            "processed_by_id": w.processed_by_id,
            "processed_at": w.processed_at,
            "created_at": w.created_at
        }
        for w in withdrawals
    ]

@router.post("/withdrawals/{withdrawal_id}/process", response_model=WithdrawalResponse)
def process_withdrawal_claim(
    withdrawal_id: int,
    req: WithdrawalProcessRequest,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    w = PaymentService.process_withdrawal(
        db=db,
        withdrawal_id=withdrawal_id,
        processor_user=current_user,
        action=req.action,
        notes=req.notes,
        ip_address=client_ip
    )

    return {
        "id": w.id,
        "user_id": w.user_id,
        "amount": w.amount,
        "amount_inr": w.amount / 100.0,
        "bank_account_number": w.bank_account_number,
        "ifsc_code": w.ifsc_code,
        "account_holder_name": w.account_holder_name,
        "upi_id": w.upi_id,
        "status": w.status,
        "notes": w.notes,
        "processed_by_id": w.processed_by_id,
        "processed_at": w.processed_at,
        "created_at": w.created_at
    }
