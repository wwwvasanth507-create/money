import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL_LOCK = "WITHDRAWAL_LOCK"
    WITHDRAWAL_PAYOUT = "WITHDRAWAL_PAYOUT"
    WITHDRAWAL_REFUND = "WITHDRAWAL_REFUND"
    BET_PLACED = "BET_PLACED"
    BET_WIN = "BET_WIN"
    BONUS_CREDIT = "BONUS_CREDIT"
    ADMIN_ADJUSTMENT = "ADMIN_ADJUSTMENT"

class TransactionStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    FAILED = "FAILED"

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    real_balance = Column(BigInteger, default=0, nullable=False)    # in paise (100 paise = 1 INR)
    bonus_balance = Column(BigInteger, default=0, nullable=False)   # in paise
    locked_balance = Column(BigInteger, default=0, nullable=False)  # in paise
    currency = Column(String(10), default="INR", nullable=False)
    version = Column(Integer, default=1, nullable=False)            # Optimistic concurrency version
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")

    @property
    def available_balance(self) -> int:
        return self.real_balance - self.locked_balance

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)             # DEPOSIT, WITHDRAWAL_LOCK, etc.
    amount = Column(BigInteger, nullable=False)           # Amount in integer paise
    balance_before = Column(BigInteger, nullable=False)   # Real balance before
    balance_after = Column(BigInteger, nullable=False)    # Real balance after
    reference_id = Column(String(100), nullable=True)     # e.g. deposit_id, withdrawal_id, session_id
    reference_type = Column(String(50), nullable=True)   # DEPOSIT, WITHDRAWAL, GAME_SESSION
    status = Column(String(20), default=TransactionStatus.SUCCESS.value, nullable=False)
    created_by = Column(String(50), nullable=False, default="SYSTEM")
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    wallet = relationship("Wallet", back_populates="transactions")
    user = relationship("User")

