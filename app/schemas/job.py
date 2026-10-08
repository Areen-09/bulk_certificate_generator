from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobStatus
from app.schemas.certificate import CertificateItemResponse, RecipientInput


class JobCreateRequest(BaseModel):
    event_name: str = Field(..., min_length=2, max_length=255, description="Event or course name")
    issuer_name: Optional[str] = Field(None, max_length=255, description="Issuing organization or authority")
    issue_date: Optional[date] = Field(None, description="Issue date (defaults to current date)")
    description: Optional[str] = Field(
        None, max_length=500, description="Achievement text or completion description"
    )
    recipients: List[RecipientInput] = Field(
        ..., min_length=1, description="List of recipient records to generate certificates for"
    )


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_count: int
    message: str
    links: Dict[str, str]


class JobCounters(BaseModel):
    total: int
    processed: int
    successful: int
    failed: int


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(alias="id")
    event_name: str
    issuer_name: str
    issue_date: date
    description: str
    status: JobStatus
    progress_percentage: float
    counters: JobCounters
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    recipients: List[CertificateItemResponse]


class JobListSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str = Field(alias="id")
    event_name: str
    issuer_name: str
    issue_date: date
    status: JobStatus
    progress_percentage: float
    total_count: int
    successful_count: int
    failed_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
