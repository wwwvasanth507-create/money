from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.user import User, ResponsibleGamingSetting
from app.models.payment import DepositRequest, DepositStatus
from app.models.wallet import WalletTransaction, TransactionType

class ResponsibleGamingService:
    @staticmethod
    def get_or_create_settings(db: Session, user_id: int) -> ResponsibleGamingSetting:
        rg = db.query(ResponsibleGamingSetting).filter(ResponsibleGamingSetting.user_id == user_id).first()
        if not rg:
            rg = ResponsibleGamingSetting(user_id=user_id)
            db.add(rg)
            db.commit()
            db.refresh(rg)
        return rg

    @staticmethod
    def check_self_exclusion(db: Session, user_id: int):
        rg = db.query(ResponsibleGamingSetting).filter(ResponsibleGamingSetting.user_id == user_id).first()
        if rg and rg.self_exclusion_until:
            if datetime.utcnow() < rg.self_exclusion_until:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account is currently self-excluded until {rg.self_exclusion_until.strftime('%Y-%m-%d %H:%M:%S UTC')} for responsible gaming protection."
                )

    @staticmethod
    def validate_deposit_limits(db: Session, user_id: int, amount_paise: int):
        rg = db.query(ResponsibleGamingSetting).filter(ResponsibleGamingSetting.user_id == user_id).first()
        if not rg:
            return

        now = datetime.utcnow()

        # Check Daily Limit
        if rg.daily_deposit_limit:
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            daily_total = db.query(func.coalesce(func.sum(DepositRequest.amount), 0)).filter(
                DepositRequest.user_id == user_id,
                DepositRequest.status == DepositStatus.APPROVED.value,
                DepositRequest.created_at >= day_start
            ).scalar() or 0

            if (daily_total + amount_paise) > rg.daily_deposit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Deposit exceeds your responsible gaming daily deposit limit of ₹{rg.daily_deposit_limit / 100:.2f}."
                )

        # Check Weekly Limit
        if rg.weekly_deposit_limit:
            week_start = now - timedelta(days=7)
            weekly_total = db.query(func.coalesce(func.sum(DepositRequest.amount), 0)).filter(
                DepositRequest.user_id == user_id,
                DepositRequest.status == DepositStatus.APPROVED.value,
                DepositRequest.created_at >= week_start
            ).scalar() or 0

            if (weekly_total + amount_paise) > rg.weekly_deposit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Deposit exceeds your responsible gaming weekly deposit limit of ₹{rg.weekly_deposit_limit / 100:.2f}."
                )

        # Check Monthly Limit
        if rg.monthly_deposit_limit:
            month_start = now - timedelta(days=30)
            monthly_total = db.query(func.coalesce(func.sum(DepositRequest.amount), 0)).filter(
                DepositRequest.user_id == user_id,
                DepositRequest.status == DepositStatus.APPROVED.value,
                DepositRequest.created_at >= month_start
            ).scalar() or 0

            if (monthly_total + amount_paise) > rg.monthly_deposit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Deposit exceeds your responsible gaming monthly deposit limit of ₹{rg.monthly_deposit_limit / 100:.2f}."
                )

    @staticmethod
    def update_settings(
        db: Session,
        user_id: int,
        daily_deposit_limit: Optional[int] = None,
        weekly_deposit_limit: Optional[int] = None,
        monthly_deposit_limit: Optional[int] = None,
        daily_loss_limit: Optional[int] = None,
        self_exclusion_days: Optional[int] = None
    ) -> ResponsibleGamingSetting:
        rg = ResponsibleGamingService.get_or_create_settings(db, user_id)

        if daily_deposit_limit is not None:
            rg.daily_deposit_limit = daily_deposit_limit
        if weekly_deposit_limit is not None:
            rg.weekly_deposit_limit = weekly_deposit_limit
        if monthly_deposit_limit is not None:
            rg.monthly_deposit_limit = monthly_deposit_limit
        if daily_loss_limit is not None:
            rg.daily_loss_limit = daily_loss_limit

        if self_exclusion_days and self_exclusion_days > 0:
            rg.self_exclusion_until = datetime.utcnow() + timedelta(days=self_exclusion_days)

        db.commit()
        db.refresh(rg)
        return rg
