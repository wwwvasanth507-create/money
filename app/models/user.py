import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, BigInteger
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class UserRole(str, enum.Enum):
    PLAYER = "PLAYER"
    PAYMENT_VERIFIER = "PAYMENT_VERIFIER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

class KYCStatus(str, enum.Enum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default=UserRole.PLAYER.value)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    kyc_document = relationship("KYCDocument", back_populates="user", uselist=False, foreign_keys="KYCDocument.user_id")
    responsible_gaming = relationship("ResponsibleGamingSetting", back_populates="user", uselist=False)

class KYCDocument(Base):
    __tablename__ = "kyc_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    document_type = Column(String(30), nullable=False)  # PAN, AADHAAR, PASSPORT
    document_number = Column(String(50), nullable=False)
    front_image_path = Column(String(255), nullable=False)
    back_image_path = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default=KYCStatus.PENDING.value)
    rejection_reason = Column(String(255), nullable=True)
    submitted_at = Column(DateTime, default=utc_now, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="kyc_document")
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])

class ResponsibleGamingSetting(Base):
    __tablename__ = "responsible_gaming_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    daily_deposit_limit = Column(BigInteger, nullable=True)  # in integer paise
    weekly_deposit_limit = Column(BigInteger, nullable=True) # in integer paise
    monthly_deposit_limit = Column(BigInteger, nullable=True)# in integer paise
    daily_loss_limit = Column(BigInteger, nullable=True)    # in integer paise
    self_exclusion_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="responsible_gaming")

