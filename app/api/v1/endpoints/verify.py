from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.certificate import CertificateRecord, CertificateStatus
from app.schemas.certificate import CertificateVerificationResponse

router = APIRouter(prefix="/certificates", tags=["Verification"])


@router.get(
    "/verify/{certificate_code}",
    response_model=CertificateVerificationResponse,
    summary="Verify certificate authenticity",
    description="Validates a public certificate verification code and retrieves official issuance metadata.",
)
async def verify_certificate(
    certificate_code: str,
    db: AsyncSession = Depends(get_db),
):
    clean_code = certificate_code.strip().upper()

    query = (
        select(CertificateRecord)
        .where(CertificateRecord.certificate_code == clean_code)
        .options(selectinload(CertificateRecord.job))
    )
    result = await db.execute(query)
    cert = result.scalar_one_or_none()

    if not cert or cert.status != CertificateStatus.COMPLETED or not cert.job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate verification failed: Code '{clean_code}' is not recognized or not authentic.",
        )

    return CertificateVerificationResponse(
        certificate_code=clean_code,
        is_valid=True,
        recipient_name=cert.recipient_name,
        event_name=cert.job.event_name,
        issuer_name=cert.job.issuer_name,
        issue_date=cert.job.issue_date,
        description=cert.job.description,
        custom_data=cert.custom_data,
        created_at=cert.created_at,
    )
