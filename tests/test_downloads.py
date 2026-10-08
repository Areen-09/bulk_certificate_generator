import io
import zipfile
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_download_single_certificate_and_zip(async_client: AsyncClient):
    """Validates individual PDF download and bulk ZIP download."""
    payload = {
        "event_name": "API Design Masterclass",
        "issuer_name": "Antigravity Engineering",
        "recipients": [
            {"recipient_name": "Bruce Wayne", "recipient_email": "bruce@wayne-enterprises.com"},
            {"recipient_name": "Diana Prince", "recipient_email": "diana@themyscira.gov"},
        ],
    }

    # 1. Create job (FastAPI BackgroundTasks processes it automatically)
    res = await async_client.post("/api/v1/certificates/jobs", json=payload)
    job_id = res.json()["job_id"]

    # 2. Retrieve job items to get certificate IDs
    status_res = await async_client.get(f"/api/v1/certificates/jobs/{job_id}")
    job_data = status_res.json()
    assert job_data["status"] == "COMPLETED"
    cert1 = job_data["recipients"][0]

    cert1_id = cert1.get("certificate_id") or cert1.get("id")

    # 3. Test individual PDF download
    download_res = await async_client.get(f"/api/v1/certificates/{cert1_id}/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert download_res.content.startswith(b"%PDF-")
    assert "Bruce_Wayne" in download_res.headers.get("content-disposition", "")

    # 4. Test bulk ZIP download
    zip_res = await async_client.get(f"/api/v1/certificates/jobs/{job_id}/download")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert "zip" in zip_res.headers.get("content-disposition", "").lower()

    # Unpack ZIP in memory and inspect contents
    with zipfile.ZipFile(io.BytesIO(zip_res.content), "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        assert any("Bruce_Wayne" in name for name in namelist)
        assert any("Diana_Prince" in name for name in namelist)
        for name in namelist:
            file_content = zf.read(name)
            assert file_content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_download_failed_certificate_returns_400(async_client: AsyncClient):
    payload = {
        "event_name": "Validation Test",
        "recipients": [
            {"recipient_name": "", "recipient_email": "bad@email"},  # Invalid
        ],
    }
    res = await async_client.post("/api/v1/certificates/jobs", json=payload)
    job_id = res.json()["job_id"]

    status_res = await async_client.get(f"/api/v1/certificates/jobs/{job_id}")
    cert = status_res.json()["recipients"][0]
    assert cert["status"] == "FAILED"

    cert_id = cert.get("certificate_id") or cert.get("id")

    # Attempt to download failed certificate
    download_res = await async_client.get(f"/api/v1/certificates/{cert_id}/download")
    assert download_res.status_code == 400
    assert "not in completed state" in download_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_nonexistent_certificate_returns_404(async_client: AsyncClient):
    download_res = await async_client.get("/api/v1/certificates/random-nonexistent-id/download")
    assert download_res.status_code == 404
