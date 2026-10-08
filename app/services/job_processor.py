import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core import database
from app.models.certificate import CertificateRecord, CertificateStatus
from app.models.job import GenerationJob, JobStatus
from app.services.certificate_generator import certificate_generator
from app.services.storage_service import storage_service

# Clean email regex with hyphen support
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def utc_now() -> datetime:
    """Returns naive UTC timestamp for SQLite/PostgreSQL compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobProcessor:
    """
    Background worker service that handles asynchronous processing of
    certificate generation jobs with per-recipient error isolation and idempotency.
    """

    @staticmethod
    def validate_recipient(name: str, email: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Validates recipient name and email format."""
        cleaned_name = name.strip() if name else ""
        if not cleaned_name:
            return False, "Recipient name cannot be empty or whitespace."
        if len(cleaned_name) < 2:
            return False, "Recipient name must be at least 2 characters."
        if len(cleaned_name) > 255:
            return False, "Recipient name exceeds maximum allowed length of 255 characters."

        if email:
            cleaned_email = email.strip()
            if not EMAIL_REGEX.match(cleaned_email):
                return False, f"Invalid email format: '{cleaned_email}'"

        return True, None

    @classmethod
    async def process_job(cls, job_id: str) -> None:
        """Processes all recipients within a job asynchronously with idempotency."""
        async with database.AsyncSessionLocal() as session:
            # 1. Fetch job with its certificates
            query = (
                select(GenerationJob)
                .where(GenerationJob.id == job_id)
                .options(selectinload(GenerationJob.certificates))
            )
            result = await session.execute(query)
            job = result.scalar_one_or_none()

            if not job:
                return

            # If already finished, do not re-process
            if job.status in (JobStatus.COMPLETED, JobStatus.PARTIALLY_FAILED, JobStatus.FAILED):
                return

            # 2. Transition job to PROCESSING
            job.status = JobStatus.PROCESSING
            await session.commit()

            # 3. Process each recipient record
            for cert_record in job.certificates:
                # If already processed in a previous attempt, skip
                if cert_record.status in (CertificateStatus.COMPLETED, CertificateStatus.FAILED):
                    continue

                # Recipient validation check
                is_valid, validation_error = cls.validate_recipient(
                    cert_record.recipient_name, cert_record.recipient_email
                )

                if not is_valid:
                    cert_record.status = CertificateStatus.FAILED
                    cert_record.error_message = validation_error
                    cert_record.completed_at = utc_now()
                    await session.commit()
                    continue

                # Recipient is valid, generate PDF
                cert_record.status = CertificateStatus.GENERATING
                await session.commit()

                unique_code = f"CERT-{uuid.uuid4().hex[:8].upper()}"

                try:
                    pdf_bytes = certificate_generator.generate_pdf(
                        recipient_name=cert_record.recipient_name.strip(),
                        event_name=job.event_name,
                        issuer_name=job.issuer_name,
                        issue_date=job.issue_date,
                        certificate_code=unique_code,
                        description=job.description,
                        custom_data=cert_record.custom_data,
                    )

                    # Persist PDF to storage
                    rel_path = storage_service.save_certificate_pdf(
                        job_id=job.id,
                        certificate_id=cert_record.id,
                        pdf_bytes=pdf_bytes,
                    )

                    cert_record.certificate_code = unique_code
                    cert_record.file_path = rel_path
                    cert_record.status = CertificateStatus.COMPLETED
                    cert_record.completed_at = utc_now()

                except Exception as exc:
                    cert_record.status = CertificateStatus.FAILED
                    cert_record.error_message = f"Certificate generation failed: {str(exc)}"
                    cert_record.completed_at = utc_now()

                await session.commit()

            # 4. Compute accurate counters directly from items
            job.successful_count = sum(
                1 for c in job.certificates if c.status == CertificateStatus.COMPLETED
            )
            job.failed_count = sum(
                1 for c in job.certificates if c.status == CertificateStatus.FAILED
            )
            job.processed_count = job.successful_count + job.failed_count

            # 5. Finalize Job Status
            if job.failed_count == 0 and job.successful_count > 0:
                job.status = JobStatus.COMPLETED
            elif job.successful_count > 0 and job.failed_count > 0:
                job.status = JobStatus.PARTIALLY_FAILED
            elif job.failed_count > 0 and job.successful_count == 0:
                job.status = JobStatus.FAILED
            else:
                job.status = JobStatus.COMPLETED

            job.completed_at = utc_now()
            await session.commit()


job_processor = JobProcessor()
