from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, KYCDocument, KYCStatus, UserRole
from app.schemas.user import KYCResponse, KYCReviewRequest
from app.api.deps import get_current_user, require_roles
from app.services.kyc_service import KYCService

router = APIRouter(prefix="", tags=["KYC Compliance"])

@router.post("/kyc/submit", response_model=KYCResponse)
def submit_kyc_document(
    document_type: str = Form(...),
    document_number: str = Form(...),
    front_file: UploadFile = File(...),
    back_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = KYCService.submit_kyc(
        db=db,
        user=current_user,
        document_type=document_type,
        document_number=document_number,
        front_file=front_file,
        back_file=back_file
    )
    return doc

@router.get("/kyc/status", response_model=Optional[KYCResponse])
def get_kyc_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(KYCDocument).filter(KYCDocument.user_id == current_user.id).first()
    return doc

@router.get("/admin/kyc/pending", response_model=List[KYCResponse])
def get_pending_kyc_list(
    current_user: User = Depends(require_roles([UserRole.PAYMENT_VERIFIER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    docs = db.query(KYCDocument).filter(KYCDocument.status == KYCStatus.PENDING.value).all()
    return docs

@router.post("/admin/kyc/{kyc_id}/review", response_model=KYCResponse)
def review_kyc_document(
    kyc_id: int,
    req: KYCReviewRequest,
    current_user: User = Depends(require_roles([UserRole.PAYMENT_VERIFIER.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
):
    doc = KYCService.review_kyc(
        db=db,
        kyc_id=kyc_id,
        reviewer=current_user,
        action=req.action,
        rejection_reason=req.rejection_reason
    )
    return doc
