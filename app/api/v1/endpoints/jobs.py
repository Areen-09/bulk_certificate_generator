from datetime import date
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.certificate import CertificateRecord
from app.models.job import GenerationJob, JobStatus
from app.schemas.certificate import CertificateItemResponse
from app.schemas.job import (
    JobAcceptedResponse,
    JobCounters,
    JobCreateRequest,
    JobListSummary,
    JobStatusResponse,
)
from app.services.job_processor import job_processor

router = APIRouter(prefix="/certificates/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit bulk certificate generation request",
    description="Accepts bulk recipient data, validates structure, creates a tracked job, and schedules background processing.",
)
async def create_generation_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if len(request.recipients) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum limit of {settings.MAX_BATCH_SIZE} recipients.",
        )

    # Create GenerationJob record
    job = GenerationJob(
        event_name=request.event_name.strip(),
        issuer_name=(request.issuer_name or settings.DEFAULT_ISSUER_NAME).strip(),
        issue_date=request.issue_date or date.today(),
        description=(request.description or "for successful participation and completion").strip(),
        status=JobStatus.PENDING,
        total_count=len(request.recipients),
        processed_count=0,
        successful_count=0,
        failed_count=0,
    )
    db.add(job)
    await db.flush()

    # Pre-populate CertificateRecords in PENDING state
    for rec in request.recipients:
        cert_record = CertificateRecord(
            job_id=job.id,
            recipient_name=rec.recipient_name,
            recipient_email=rec.recipient_email,
            custom_data=rec.custom_data,
        )
        db.add(cert_record)

    await db.commit()
    await db.refresh(job)

    # Enqueue background task
    background_tasks.add_task(job_processor.process_job, job.id)

    return JobAcceptedResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        message="Certificate generation job accepted and scheduled for processing.",
        links={
            "status": f"{settings.API_V1_PREFIX}/certificates/jobs/{job.id}",
            "download_zip": f"{settings.API_V1_PREFIX}/certificates/jobs/{job.id}/download",
        },
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and progress",
    description="Retrieves the real-time status, progress counters, and individual recipient certificate items for a job.",
)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    query = (
        select(GenerationJob)
        .where(GenerationJob.id == job_id)
        .options(selectinload(GenerationJob.certificates))
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate generation job '{job_id}' not found.",
        )

    # Format recipient items with direct download URLs
    recipients_data = []
    for cert in job.certificates:
        download_url = (
            f"{settings.API_V1_PREFIX}/certificates/{cert.id}/download"
            if cert.file_path and cert.status.value == "COMPLETED"
            else None
        )
        recipients_data.append(
            CertificateItemResponse(
                certificate_id=cert.id,
                recipient_name=cert.recipient_name,
                recipient_email=cert.recipient_email,
                certificate_code=cert.certificate_code,
                status=cert.status,
                download_url=download_url,
                error_message=cert.error_message,
                custom_data=cert.custom_data,
                created_at=cert.created_at,
                completed_at=cert.completed_at,
            )
        )

    return JobStatusResponse(
        id=job.id,
        event_name=job.event_name,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        description=job.description,
        status=job.status,
        progress_percentage=job.calculate_progress(),
        counters=JobCounters(
            total=job.total_count,
            processed=job.processed_count,
            successful=job.successful_count,
            failed=job.failed_count,
        ),
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        recipients=recipients_data,
    )


@router.get(
    "",
    response_model=List[JobListSummary],
    summary="List recent certificate generation jobs",
    description="Returns a paginated list of certificate generation jobs with status and summary metrics.",
)
async def list_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(GenerationJob)
        .order_by(desc(GenerationJob.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        JobListSummary(
            id=job.id,
            event_name=job.event_name,
            issuer_name=job.issuer_name,
            issue_date=job.issue_date,
            status=job.status,
            progress_percentage=job.calculate_progress(),
            total_count=job.total_count,
            successful_count=job.successful_count,
            failed_count=job.failed_count,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]
