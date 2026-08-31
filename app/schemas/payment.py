from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.payment import DepositStatus, WithdrawalStatus

class DepositCreateRequest(BaseModel):
    utr_number: str
    amount: int  # in paise (or converted from float input)

class DepositVerifyRequest(BaseModel):
    action: str  # APPROVE, REJECT, REQUEST_INFO
    verifier_notes: str

class DepositResponse(BaseModel):
    id: int
    user_id: int
    utr_number: str
    amount: int
    amount_inr: float
    payment_method: str
    proof_image_path: Optional[str] = None
    status: DepositStatus
    verifier_notes: Optional[str] = None
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WithdrawalCreateRequest(BaseModel):
    amount: int # in paise
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_holder_name: Optional[str] = None
    upi_id: Optional[str] = None

class WithdrawalProcessRequest(BaseModel):
    action: str # APPROVE or REJECT
    notes: Optional[str] = None

class WithdrawalResponse(BaseModel):
    id: int
    user_id: int
    amount: int
    amount_inr: float
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_holder_name: Optional[str] = None
    upi_id: Optional[str] = None
    status: WithdrawalStatus
    notes: Optional[str] = None
    processed_by_id: Optional[int] = None
    processed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaymentConfigUpdate(BaseModel):
    upi_id: Optional[str] = None
    qr_code_url: Optional[str] = None
    min_deposit: Optional[int] = None
    max_deposit: Optional[int] = None
    min_withdrawal: Optional[int] = None
    max_withdrawal: Optional[int] = None
    min_deposit_inr: Optional[float] = None
    max_deposit_inr: Optional[float] = None
    min_withdrawal_inr: Optional[float] = None
    max_withdrawal_inr: Optional[float] = None
    is_active: Optional[bool] = None

class PaymentConfigResponse(BaseModel):
    id: int
    upi_id: str
    qr_code_url: Optional[str] = None
    min_deposit: int
    max_deposit: int
    min_withdrawal: int
    max_withdrawal: int
    min_deposit_inr: Optional[float] = None
    max_deposit_inr: Optional[float] = None
    min_withdrawal_inr: Optional[float] = None
    max_withdrawal_inr: Optional[float] = None
    is_active: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

