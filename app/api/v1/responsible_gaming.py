from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import ResponsibleGamingUpdate, ResponsibleGamingResponse
from app.api.deps import get_current_user
from app.services.responsible_gaming_service import ResponsibleGamingService

router = APIRouter(prefix="/responsible-gaming", tags=["Responsible Gaming"])

@router.get("/settings", response_model=ResponsibleGamingResponse)
def get_rg_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rg = ResponsibleGamingService.get_or_create_settings(db, current_user.id)
    return rg

@router.post("/settings", response_model=ResponsibleGamingResponse)
def update_rg_settings(
    req: ResponsibleGamingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rg = ResponsibleGamingService.update_settings(
        db=db,
        user_id=current_user.id,
        daily_deposit_limit=req.daily_deposit_limit,
        weekly_deposit_limit=req.weekly_deposit_limit,
        monthly_deposit_limit=req.monthly_deposit_limit,
        daily_loss_limit=req.daily_loss_limit,
        self_exclusion_days=req.self_exclusion_days
    )
    return rg
