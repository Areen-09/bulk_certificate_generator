import re
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.certificate import CertificateRecord, CertificateStatus
from app.models.job import GenerationJob
from app.services.storage_service import storage_service

router = APIRouter(tags=["Certificates & Downloads"])


def sanitize_filename(name: str) -> str:
    """Sanitizes names for safe Content-Disposition headers."""
    clean = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")
    return clean or "certificate"


@router.get(
    "/certificates/{certificate_id}/download",
    summary="Download single certificate PDF",
    description="Streams the generated PDF certificate for an individual recipient.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns the generated certificate PDF file.",
        },
        404: {"description": "Certificate not found or not yet generated."},
    },
)
async def download_single_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
):
    query = select(CertificateRecord).where(CertificateRecord.id == certificate_id)
    result = await db.execute(query)
    cert = result.scalar_one_or_none()

    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found.",
        )

    if cert.status != CertificateStatus.COMPLETED or not cert.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate '{certificate_id}' is not in COMPLETED state (current: {cert.status.value}). Reason: {cert.error_message or 'Generation in progress'}",
        )

    pdf_bytes = storage_service.get_file_bytes(cert.file_path)
    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file could not be located on disk.",
        )

    safe_name = sanitize_filename(cert.recipient_name)
    code = cert.certificate_code or cert.id[:8]
    filename = f"{safe_name}_{code}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/certificates/jobs/{job_id}/download",
    summary="Download bulk certificates ZIP",
    description="Archives all successfully generated certificates in the job into a downloadable ZIP file.",
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "Returns a ZIP file containing all successful certificates.",
        },
        404: {"description": "Job not found."},
        400: {"description": "No certificates available for download."},
    },
)
async def download_job_certificates_zip(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
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

    completed_certs = [
        c for c in job.certificates if c.status == CertificateStatus.COMPLETED and c.file_path
    ]

    if not completed_certs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No successfully generated certificates available to download for job '{job_id}'. Current job status: {job.status.value}.",
        )

    # Prepare archive entries: (relative_path, arcname)
    archive_items = []
    for cert in completed_certs:
        safe_name = sanitize_filename(cert.recipient_name)
        code = cert.certificate_code or cert.id[:8]
        filename = f"{safe_name}_{code}.pdf"
        archive_items.append((cert.file_path, filename))

    zip_bytes = storage_service.create_job_zip(job.id, archive_items)
    safe_event = sanitize_filename(job.event_name)
    zip_filename = f"{safe_event}_certificates_{job.id[:8]}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
