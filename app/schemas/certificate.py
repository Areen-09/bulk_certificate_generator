from datetime import date, datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.certificate import CertificateStatus


class RecipientInput(BaseModel):
    recipient_name: str = Field(..., description="Full name of the certificate recipient")
    recipient_email: Optional[str] = Field(None, description="Email address of the recipient")
    custom_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata (e.g. grade, completion hours)"
    )


class CertificateItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    certificate_id: str
    recipient_name: str
    recipient_email: Optional[str] = None
    certificate_code: Optional[str] = None
    status: CertificateStatus
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class CertificateVerificationResponse(BaseModel):
    certificate_code: str
    is_valid: bool
    recipient_name: Optional[str] = None
    event_name: Optional[str] = None
    issuer_name: Optional[str] = None
    issue_date: Optional[date] = None
    description: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
