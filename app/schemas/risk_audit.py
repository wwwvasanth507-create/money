from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict
from app.models.risk_audit import FlagType, RiskSeverity, RiskStatus

class RiskFlagResponse(BaseModel):
    id: int
    user_id: int
    flag_type: str
    severity: str
    details: Optional[Any] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RiskFlagResolveRequest(BaseModel):
    status: RiskStatus # RESOLVED or DISMISSED

class AuditLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    target_type: str
    target_id: Optional[str] = None
    changes: Optional[Any] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
