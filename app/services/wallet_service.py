from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.wallet import Wallet, WalletTransaction, TransactionType, TransactionStatus
from app.models.user import User

class WalletService:
    @staticmethod
    def get_or_create_wallet(db: Session, user_id: int) -> Wallet:
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            wallet = Wallet(user_id=user_id, real_balance=0, bonus_balance=0, locked_balance=0)
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
        return wallet

    @staticmethod
    def credit_wallet(
        db: Session,
        user_id: int,
        amount_paise: int,
        trans_type: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        created_by: str = "SYSTEM",
        description: Optional[str] = None
    ) -> Tuple[Wallet, WalletTransaction]:
        if amount_paise <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit amount must be greater than zero."
            )

        wallet = WalletService.get_or_create_wallet(db, user_id)
        balance_before = wallet.real_balance
        balance_after = balance_before + amount_paise

        wallet.real_balance = balance_after
        wallet.version += 1

        tx = WalletTransaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=trans_type,
            amount=amount_paise,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_id=reference_id,
            reference_type=reference_type,
            status=TransactionStatus.SUCCESS.value,
            created_by=created_by,
            description=description or f"Credited ₹{amount_paise / 100:.2f} to wallet."
        )

        db.add(tx)
        db.commit()
        db.refresh(wallet)
        db.refresh(tx)
        return wallet, tx

    @staticmethod
    def debit_wallet(
        db: Session,
        user_id: int,
        amount_paise: int,
        trans_type: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        created_by: str = "SYSTEM",
        description: Optional[str] = None
    ) -> Tuple[Wallet, WalletTransaction]:
        if amount_paise <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debit amount must be greater than zero."
            )

        wallet = WalletService.get_or_create_wallet(db, user_id)
        if wallet.available_balance < amount_paise:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient available balance. Available: ₹{wallet.available_balance / 100:.2f}, Required: ₹{amount_paise / 100:.2f}"
            )

        balance_before = wallet.real_balance
        balance_after = balance_before - amount_paise

        wallet.real_balance = balance_after
        wallet.version += 1

        tx = WalletTransaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=trans_type,
            amount=amount_paise,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_id=reference_id,
            reference_type=reference_type,
            status=TransactionStatus.SUCCESS.value,
            created_by=created_by,
            description=description or f"Debited ₹{amount_paise / 100:.2f} from wallet."
        )

        db.add(tx)
        db.commit()
        db.refresh(wallet)
        db.refresh(tx)
        return wallet, tx

    @staticmethod
    def lock_funds(
        db: Session,
        user_id: int,
        amount_paise: int,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[Wallet, WalletTransaction]:
        if amount_paise <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lock amount must be greater than zero."
            )

        wallet = WalletService.get_or_create_wallet(db, user_id)
        if wallet.available_balance < amount_paise:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient available balance to lock funds. Available: ₹{wallet.available_balance / 100:.2f}"
            )

        wallet.locked_balance += amount_paise
        wallet.version += 1

        tx = WalletTransaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=TransactionType.WITHDRAWAL_LOCK.value,
            amount=amount_paise,
            balance_before=wallet.real_balance,
            balance_after=wallet.real_balance,
            reference_id=reference_id,
            reference_type=reference_type or "WITHDRAWAL",
            status=TransactionStatus.SUCCESS.value,
            created_by="SYSTEM",
            description=description or f"Locked ₹{amount_paise / 100:.2f} for withdrawal request."
        )

        db.add(tx)
        db.commit()
        db.refresh(wallet)
        db.refresh(tx)
        return wallet, tx

    @staticmethod
    def release_locked_funds(
        db: Session,
        user_id: int,
        amount_paise: int,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[Wallet, WalletTransaction]:
        wallet = WalletService.get_or_create_wallet(db, user_id)
        if wallet.locked_balance < amount_paise:
            amount_paise = wallet.locked_balance

        wallet.locked_balance -= amount_paise
        wallet.version += 1

        tx = WalletTransaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=TransactionType.WITHDRAWAL_REFUND.value,
            amount=amount_paise,
            balance_before=wallet.real_balance,
            balance_after=wallet.real_balance,
            reference_id=reference_id,
            reference_type=reference_type or "WITHDRAWAL",
            status=TransactionStatus.SUCCESS.value,
            created_by="SYSTEM",
            description=description or f"Unlocked ₹{amount_paise / 100:.2f} back to available balance."
        )

        db.add(tx)
        db.commit()
        db.refresh(wallet)
        db.refresh(tx)
        return wallet, tx

    @staticmethod
    def settle_locked_funds(
        db: Session,
        user_id: int,
        amount_paise: int,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        description: Optional[str] = None
    ) -> Tuple[Wallet, WalletTransaction]:
        wallet = WalletService.get_or_create_wallet(db, user_id)
        if wallet.locked_balance < amount_paise:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Locked balance mismatch for settlement."
            )

        balance_before = wallet.real_balance
        balance_after = balance_before - amount_paise

        wallet.real_balance = balance_after
        wallet.locked_balance -= amount_paise
        wallet.version += 1

        tx = WalletTransaction(
            user_id=user_id,
            wallet_id=wallet.id,
            type=TransactionType.WITHDRAWAL_PAYOUT.value,
            amount=amount_paise,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_id=reference_id,
            reference_type=reference_type or "WITHDRAWAL",
            status=TransactionStatus.SUCCESS.value,
            created_by="SYSTEM",
            description=description or f"Completed withdrawal payout of ₹{amount_paise / 100:.2f}."
        )

        db.add(tx)
        db.commit()
        db.refresh(wallet)
        db.refresh(tx)
        return wallet, tx
