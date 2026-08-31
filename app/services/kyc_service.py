import os
import io
from datetime import datetime
from typing import Optional
from PIL import Image
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from app.models.user import User, KYCDocument, KYCStatus
from app.config import settings

class KYCService:
    ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

    @staticmethod
    def validate_and_save_image(file: UploadFile, user_id: int, prefix: str) -> str:
        """Validates file magic bytes via Pillow to prevent malicious image file uploads."""
        contents = file.file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        try:
            image = Image.open(io.BytesIO(contents))
            image.verify()  # Verify header and magic bytes
            img_format = image.format
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file format. Image magic bytes verification failed."
            )

        if img_format not in KYCService.ALLOWED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format ({img_format}). Allowed formats: JPEG, PNG, WEBP."
            )

        ext = "jpg" if img_format == "JPEG" else img_format.lower()
        filename = f"{user_id}_{prefix}_{int(datetime.utcnow().timestamp())}.{ext}"
        filepath = os.path.join(settings.UPLOAD_DIR, "kyc", filename)

        # Write file to disk securely
        with open(filepath, "wb") as f:
            f.write(contents)

        return f"/uploads/kyc/{filename}"

    @staticmethod
    def submit_kyc(
        db: Session,
        user: User,
        document_type: str,
        document_number: str,
        front_file: UploadFile,
        back_file: Optional[UploadFile] = None
    ) -> KYCDocument:
        front_path = KYCService.validate_and_save_image(front_file, user.id, "front")
        back_path = KYCService.validate_and_save_image(back_file, user.id, "back") if back_file else None

        doc = db.query(KYCDocument).filter(KYCDocument.user_id == user.id).first()
        if not doc:
            doc = KYCDocument(
                user_id=user.id,
                document_type=document_type.upper(),
                document_number=document_number.strip(),
                front_image_path=front_path,
                back_image_path=back_path,
                status=KYCStatus.PENDING.value
            )
            db.add(doc)
        else:
            doc.document_type = document_type.upper()
            doc.document_number = document_number.strip()
            doc.front_image_path = front_path
            doc.back_image_path = back_path
            doc.status = KYCStatus.PENDING.value
            doc.rejection_reason = None
            doc.submitted_at = datetime.utcnow()

        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def review_kyc(
        db: Session,
        kyc_id: int,
        reviewer: User,
        action: str, # APPROVE or REJECT
        rejection_reason: Optional[str] = None
    ) -> KYCDocument:
        doc = db.query(KYCDocument).filter(KYCDocument.id == kyc_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC document not found.")

        if action.upper() == "APPROVE":
            doc.status = KYCStatus.APPROVED.value
            doc.reviewed_at = datetime.utcnow()
            doc.reviewed_by_id = reviewer.id

            # Mark user as verified
            user = db.query(User).filter(User.id == doc.user_id).first()
            if user:
                user.is_verified = True
        elif action.upper() == "REJECT":
            doc.status = KYCStatus.REJECTED.value
            doc.rejection_reason = rejection_reason or "Document verification failed."
            doc.reviewed_at = datetime.utcnow()
            doc.reviewed_by_id = reviewer.id
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid KYC review action.")

        db.commit()
        db.refresh(doc)
        return doc
