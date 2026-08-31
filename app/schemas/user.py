from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.user import UserRole, KYCStatus

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class VerifierCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class KYCSubmitRequest(BaseModel):
    document_type: str
    document_number: str

class KYCResponse(BaseModel):
    id: int
    user_id: int
    document_type: str
    document_number: str
    front_image_path: str
    back_image_path: Optional[str] = None
    status: KYCStatus
    rejection_reason: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class KYCReviewRequest(BaseModel):
    action: str # APPROVE or REJECT
    rejection_reason: Optional[str] = None

class ResponsibleGamingUpdate(BaseModel):
    daily_deposit_limit: Optional[int] = None   # in paise
    weekly_deposit_limit: Optional[int] = None  # in paise
    monthly_deposit_limit: Optional[int] = None # in paise
    daily_loss_limit: Optional[int] = None     # in paise
    self_exclusion_days: Optional[int] = None

class ResponsibleGamingResponse(BaseModel):
    user_id: int
    daily_deposit_limit: Optional[int] = None
    weekly_deposit_limit: Optional[int] = None
    monthly_deposit_limit: Optional[int] = None
    daily_loss_limit: Optional[int] = None
    self_exclusion_until: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
