import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class DepositStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INFO_REQUESTED = "INFO_REQUESTED"

class WithdrawalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class PaymentConfiguration(Base):
    __tablename__ = "payment_configurations"

    id = Column(Integer, primary_key=True, index=True)
    upi_id = Column(String(100), nullable=False, default="auragaming@upi")
    qr_code_url = Column(String(255), nullable=True)
    min_deposit = Column(BigInteger, default=10000, nullable=False)     # ₹100 = 10,000 paise
    max_deposit = Column(BigInteger, default=5000000, nullable=False)   # ₹50,000 = 5,000,000 paise
    min_withdrawal = Column(BigInteger, default=50000, nullable=False)   # ₹500 = 50,000 paise
    max_withdrawal = Column(BigInteger, default=10000000, nullable=False)# ₹100,000 = 10,000,000 paise
    is_active = Column(Boolean, default=True, nullable=False)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

class DepositRequest(Base):
    __tablename__ = "deposit_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    utr_number = Column(String(50), unique=True, nullable=False, index=True) # Unique constraint for duplicate detection
    amount = Column(BigInteger, nullable=False)                               # Amount in paise
    payment_method = Column(String(30), default="UPI", nullable=False)
    proof_image_path = Column(String(255), nullable=True)
    status = Column(String(20), default=DepositStatus.PENDING.value, nullable=False, index=True)
    verifier_notes = Column(String(255), nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])
    verifier = relationship("User", foreign_keys=[verified_by_id])

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False) # Amount in paise
    bank_account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    account_holder_name = Column(String(100), nullable=True)
    upi_id = Column(String(100), nullable=True)
    status = Column(String(20), default=WithdrawalStatus.PENDING.value, nullable=False, index=True)
    notes = Column(String(255), nullable=True)
    processed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])
    processor = relationship("User", foreign_keys=[processed_by_id])

