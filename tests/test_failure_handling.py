import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_handling_individual_certificate_failure(async_client: AsyncClient):
    """
    Validates failure isolation:
    A failure while generating one certificate must NOT prevent other valid
    certificates in the same job from being generated.
    """
    payload = {
        "event_name": "Fullstack Cloud Certification",
        "issuer_name": "Cloud Academy",
        "recipients": [
            {
                "recipient_name": "Alice Johnson",
                "recipient_email": "alice@example.com",
                "custom_data": {"grade": "Distinction"},
            },
            {
                "recipient_name": "   ",  # Invalid: whitespace name
                "recipient_email": "badname@example.com",
            },
            {
                "recipient_name": "Charlie Brown",
                "recipient_email": "not-a-valid-email",  # Invalid: bad email format
            },
        ],
    }

    # 1. Submit bulk job (processed in background)
    create_res = await async_client.post("/api/v1/certificates/jobs", json=payload)
    assert create_res.status_code == 202
    job_id = create_res.json()["job_id"]

    # 2. Retrieve status
    status_res = await async_client.get(f"/api/v1/certificates/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()

    # Job level state checks
    assert job_data["status"] == "PARTIALLY_FAILED"
    assert job_data["progress_percentage"] == 100.0
    assert job_data["counters"]["total"] == 3
    assert job_data["counters"]["processed"] == 3
    assert job_data["counters"]["successful"] == 1
    assert job_data["counters"]["failed"] == 2

    recipients = job_data["recipients"]
    assert len(recipients) == 3

    # Recipient 1: Valid
    alice = next(r for r in recipients if r["recipient_name"] == "Alice Johnson")
    assert alice["status"] == "COMPLETED"
    assert alice["certificate_code"] is not None
    assert alice["certificate_code"].startswith("CERT-")
    assert alice["download_url"] is not None
    assert alice["error_message"] is None

    # Recipient 2: Empty name failure
    empty_rec = next(r for r in recipients if r["recipient_name"] == "   ")
    assert empty_rec["status"] == "FAILED"
    assert empty_rec["certificate_code"] is None
    assert empty_rec["download_url"] is None
    assert "empty" in empty_rec["error_message"].lower()

    # Recipient 3: Invalid email failure
    bad_email_rec = next(r for r in recipients if r["recipient_name"] == "Charlie Brown")
    assert bad_email_rec["status"] == "FAILED"
    assert bad_email_rec["download_url"] is None
    assert "invalid email" in bad_email_rec["error_message"].lower()


@pytest.mark.asyncio
async def test_fully_failed_job(async_client: AsyncClient):
    """Validates that a job where 100% of recipients fail is marked FAILED."""
    payload = {
        "event_name": "Strict Test Workshop",
        "recipients": [
            {"recipient_name": "", "recipient_email": "bad1"},
            {"recipient_name": " ", "recipient_email": "bad2"},
        ],
    }

    create_res = await async_client.post("/api/v1/certificates/jobs", json=payload)
    job_id = create_res.json()["job_id"]

    status_res = await async_client.get(f"/api/v1/certificates/jobs/{job_id}")
    job_data = status_res.json()

    assert job_data["status"] == "FAILED"
    assert job_data["counters"]["successful"] == 0
    assert job_data["counters"]["failed"] == 2
