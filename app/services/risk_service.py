import json
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.risk_audit import RiskFlag, FlagType, RiskSeverity, RiskStatus
from app.models.user import User

class RiskService:
    @staticmethod
    def create_flag(
        db: Session,
        user_id: int,
        flag_type: str,
        severity: str = RiskSeverity.MEDIUM.value,
        details: Optional[dict] = None
    ) -> RiskFlag:
        flag = RiskFlag(
            user_id=user_id,
            flag_type=flag_type,
            severity=severity,
            details=json.dumps(details) if details else None,
            status=RiskStatus.OPEN.value
        )
        db.add(flag)
        db.commit()
        db.refresh(flag)
        return flag

    @staticmethod
    def list_flags(db: Session, status_filter: Optional[str] = None) -> List[RiskFlag]:
        query = db.query(RiskFlag)
        if status_filter:
            query = query.filter(RiskFlag.status == status_filter.upper())
        return query.order_by(RiskFlag.created_at.desc()).all()

    @staticmethod
    def update_flag_status(db: Session, flag_id: int, new_status: str) -> RiskFlag:
        flag = db.query(RiskFlag).filter(RiskFlag.id == flag_id).first()
        if not flag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk flag not found.")
        flag.status = new_status.upper()
        db.commit()
        db.refresh(flag)
        return flag
