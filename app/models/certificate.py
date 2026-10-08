import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.job import GenerationJob


class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CertificateRecord(Base):
    __tablename__ = "certificate_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Public verification code
    certificate_code: Mapped[str | None] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )
    
    # Additional flexible metadata (grade, hours, instructor)
    custom_data: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    status: Mapped[CertificateStatus] = mapped_column(
        Enum(CertificateStatus), default=CertificateStatus.PENDING, nullable=False, index=True
    )
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="certificates")
