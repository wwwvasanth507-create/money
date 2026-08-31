import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class FlagType(str, enum.Enum):
    DUPLICATE_UTR_ATTEMPT = "DUPLICATE_UTR_ATTEMPT"
    HIGH_VELOCITY_WITHDRAWAL = "HIGH_VELOCITY_WITHDRAWAL"
    MULTIPLE_ACCOUNT_IP_MATCH = "MULTIPLE_ACCOUNT_IP_MATCH"
    UNUSUAL_WIN_RATE = "UNUSUAL_WIN_RATE"
    LARGE_UNVERIFIED_DEPOSIT = "LARGE_UNVERIFIED_DEPOSIT"

class RiskSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    flag_type = Column(String(50), nullable=False)
    severity = Column(String(20), default=RiskSeverity.MEDIUM.value, nullable=False)
    details = Column(Text, nullable=True) # JSON details
    status = Column(String(20), default=RiskStatus.OPEN.value, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(100), nullable=True)
    changes = Column(Text, nullable=True) # JSON snapshot
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)

    admin = relationship("User")

