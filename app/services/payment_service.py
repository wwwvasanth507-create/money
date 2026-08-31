import json
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.payment import PaymentConfiguration, DepositRequest, WithdrawalRequest, DepositStatus, WithdrawalStatus
from app.models.user import User, UserRole
from app.models.risk_audit import RiskFlag, FlagType, RiskSeverity, AuditLog
from app.services.wallet_service import WalletService
from app.models.wallet import TransactionType

class PaymentService:
    @staticmethod
    def get_or_create_config(db: Session) -> PaymentConfiguration:
        config = db.query(PaymentConfiguration).first()
        if not config:
            config = PaymentConfiguration(
                upi_id="auragaming@upi",
                min_deposit=10000,      # ₹100
                max_deposit=5000000,    # ₹50,000
                min_withdrawal=50000,   # ₹500
                max_withdrawal=10000000 # ₹100,000
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    @staticmethod
    def submit_deposit(
        db: Session,
        user_id: int,
        utr_number: str,
        amount_paise: int,
        proof_image_path: Optional[str] = None
    ) -> DepositRequest:
        config = PaymentService.get_or_create_config(db)
        if amount_paise < config.min_deposit or amount_paise > config.max_deposit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deposit amount must be between ₹{config.min_deposit / 100:.2f} and ₹{config.max_deposit / 100:.2f}"
            )

        utr_clean = utr_number.strip().upper()

        # Check existing UTR claim
        existing = db.query(DepositRequest).filter(DepositRequest.utr_number == utr_clean).first()
        if existing:
            # Raise Anti-Fraud Risk Flag
            risk_flag = RiskFlag(
                user_id=user_id,
                flag_type=FlagType.DUPLICATE_UTR_ATTEMPT.value,
                severity=RiskSeverity.HIGH.value,
                details=json.dumps({
                    "attempted_utr": utr_clean,
                    "attempted_amount_paise": amount_paise,
                    "original_deposit_id": existing.id,
                    "original_user_id": existing.user_id
                })
            )
            db.add(risk_flag)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This UTR transaction reference has already been submitted. Repeated attempts may lock your account."
            )

        deposit_req = DepositRequest(
            user_id=user_id,
            utr_number=utr_clean,
            amount=amount_paise,
            payment_method="UPI",
            proof_image_path=proof_image_path,
            status=DepositStatus.PENDING.value
        )

        try:
            db.add(deposit_req)
            db.commit()
            db.refresh(deposit_req)
        except IntegrityError:
            db.rollback()
            # Double check duplicate UTR
            risk_flag = RiskFlag(
                user_id=user_id,
                flag_type=FlagType.DUPLICATE_UTR_ATTEMPT.value,
                severity=RiskSeverity.HIGH.value,
                details=json.dumps({"attempted_utr": utr_clean})
            )
            db.add(risk_flag)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate UTR submission detected."
            )

        return deposit_req

    @staticmethod
    def verify_deposit(
        db: Session,
        deposit_id: int,
        verifier_user: User,
        action: str, # APPROVE, REJECT, REQUEST_INFO
        verifier_notes: str,
        ip_address: Optional[str] = None
    ) -> DepositRequest:
        if verifier_user.role not in [UserRole.PAYMENT_VERIFIER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: Payment Verifier privileges required."
            )

        if not verifier_notes or not verifier_notes.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mandatory verification notes required for verification action."
            )

        deposit_req = db.query(DepositRequest).filter(DepositRequest.id == deposit_id).first()
        if not deposit_req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deposit request not found.")

        if deposit_req.status != DepositStatus.PENDING.value and deposit_req.status != DepositStatus.INFO_REQUESTED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Deposit is already processed with status: {deposit_req.status}")

        action_upper = action.upper()
        now_utc = datetime.now(timezone.utc)
        if action_upper == "APPROVE":
            deposit_req.status = DepositStatus.APPROVED.value
            deposit_req.verifier_notes = verifier_notes.strip()
            deposit_req.verified_by_id = verifier_user.id
            deposit_req.verified_at = now_utc

            # Atomic double-entry credit
            WalletService.credit_wallet(
                db=db,
                user_id=deposit_req.user_id,
                amount_paise=deposit_req.amount,
                trans_type=TransactionType.DEPOSIT.value,
                reference_id=str(deposit_req.id),
                reference_type="DEPOSIT",
                created_by=f"VERIFIER:{verifier_user.username}",
                description=f"Manual UPI Deposit Approved (UTR: {deposit_req.utr_number}). Note: {verifier_notes.strip()}"
            )

        elif action_upper == "REJECT":
            deposit_req.status = DepositStatus.REJECTED.value
            deposit_req.verifier_notes = verifier_notes.strip()
            deposit_req.verified_by_id = verifier_user.id
            deposit_req.verified_at = now_utc

        elif action_upper == "REQUEST_INFO":
            deposit_req.status = DepositStatus.INFO_REQUESTED.value
            deposit_req.verifier_notes = verifier_notes.strip()
            deposit_req.verified_by_id = verifier_user.id
            deposit_req.verified_at = now_utc
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification action.")

        # Log audit trail
        audit = AuditLog(
            admin_id=verifier_user.id,
            action=f"VERIFY_DEPOSIT_{action_upper}",
            target_type="DepositRequest",
            target_id=str(deposit_req.id),
            changes=json.dumps({
                "utr": deposit_req.utr_number,
                "amount": deposit_req.amount,
                "status": deposit_req.status,
                "notes": verifier_notes
            }),
            ip_address=ip_address
        )
        db.add(audit)
        db.commit()
        db.refresh(deposit_req)
        return deposit_req

    @staticmethod
    def submit_withdrawal(
        db: Session,
        user_id: int,
        amount_paise: int,
        bank_account_number: Optional[str] = None,
        ifsc_code: Optional[str] = None,
        account_holder_name: Optional[str] = None,
        upi_id: Optional[str] = None
    ) -> WithdrawalRequest:
        config = PaymentService.get_or_create_config(db)
        if amount_paise < config.min_withdrawal or amount_paise > config.max_withdrawal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Withdrawal amount must be between ₹{config.min_withdrawal / 100:.2f} and ₹{config.max_withdrawal / 100:.2f}"
            )

        if not upi_id and (not bank_account_number or not ifsc_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either UPI ID or Bank Details (Account Number & IFSC) must be provided."
            )

        withdrawal_req = WithdrawalRequest(
            user_id=user_id,
            amount=amount_paise,
            bank_account_number=bank_account_number,
            ifsc_code=ifsc_code,
            account_holder_name=account_holder_name,
            upi_id=upi_id,
            status=WithdrawalStatus.PENDING.value
        )
        db.add(withdrawal_req)
        db.flush()

        # Atomic lock of funds on wallet
        WalletService.lock_funds(
            db=db,
            user_id=user_id,
            amount_paise=amount_paise,
            reference_id=str(withdrawal_req.id),
            reference_type="WITHDRAWAL",
            description=f"Withdrawal request #{withdrawal_req.id} submitted."
        )

        db.commit()
        db.refresh(withdrawal_req)
        return withdrawal_req

    @staticmethod
    def process_withdrawal(
        db: Session,
        withdrawal_id: int,
        processor_user: User,
        action: str, # APPROVE or REJECT
        notes: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> WithdrawalRequest:
        if processor_user.role not in [UserRole.PAYMENT_VERIFIER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: Verifier or Admin privileges required to process withdrawals."
            )

        w_req = db.query(WithdrawalRequest).filter(WithdrawalRequest.id == withdrawal_id).first()
        if not w_req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal request not found.")

        if w_req.status != WithdrawalStatus.PENDING.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Withdrawal already processed with status: {w_req.status}")

        action_upper = action.upper()
        now_utc = datetime.now(timezone.utc)
        if action_upper == "APPROVE":
            w_req.status = WithdrawalStatus.APPROVED.value
            w_req.notes = notes or "Withdrawal payout completed."
            w_req.processed_by_id = processor_user.id
            w_req.processed_at = now_utc

            WalletService.settle_locked_funds(
                db=db,
                user_id=w_req.user_id,
                amount_paise=w_req.amount,
                reference_id=str(w_req.id),
                reference_type="WITHDRAWAL",
                description=f"Withdrawal #{w_req.id} approved and paid out."
            )

        elif action_upper == "REJECT":
            w_req.status = WithdrawalStatus.REJECTED.value
            w_req.notes = notes or "Withdrawal request rejected."
            w_req.processed_by_id = processor_user.id
            w_req.processed_at = now_utc

            WalletService.release_locked_funds(
                db=db,
                user_id=w_req.user_id,
                amount_paise=w_req.amount,
                reference_id=str(w_req.id),
                reference_type="WITHDRAWAL",
                description=f"Withdrawal #{w_req.id} rejected. Funds unlocked."
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid withdrawal action.")

        # Log audit trail
        audit = AuditLog(
            admin_id=processor_user.id,
            action=f"PROCESS_WITHDRAWAL_{action_upper}",
            target_type="WithdrawalRequest",
            target_id=str(w_req.id),
            changes=json.dumps({
                "amount": w_req.amount,
                "status": w_req.status,
                "notes": notes
            }),
            ip_address=ip_address
        )
        db.add(audit)
        db.commit()
        db.refresh(w_req)
        return w_req
