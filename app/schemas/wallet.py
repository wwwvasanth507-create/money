from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.wallet import TransactionType, TransactionStatus

class WalletResponse(BaseModel):
    id: int
    user_id: int
    real_balance: int      # in paise
    bonus_balance: int     # in paise
    locked_balance: int    # in paise
    available_balance: int # in paise
    real_balance_inr: float
    available_balance_inr: float
    currency: str = "INR"

    model_config = ConfigDict(from_attributes=True)

class WalletTransactionResponse(BaseModel):
    id: int
    transaction_id: str
    user_id: int
    type: str
    amount: int            # in paise
    amount_inr: float
    balance_before: int    # in paise
    balance_after: int     # in paise
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    status: str
    created_by: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
