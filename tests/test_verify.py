import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_verify_certificate_endpoint(async_client: AsyncClient):
    payload = {
        "event_name": "Cryptography & Zero Knowledge Systems",
        "issuer_name": "Antigravity Research Labs",
        "issue_date": "2026-10-08",
        "description": "for completing cryptographic protocol design",
        "recipients": [
            {"recipient_name": "Satoshi Nakamoto", "recipient_email": "satoshi@gmx.com"},
        ],
    }

    # 1. Create job (processed automatically)
    res = await async_client.post("/api/v1/certificates/jobs", json=payload)
    job_id = res.json()["job_id"]

    # 2. Get verification code
    status_res = await async_client.get(f"/api/v1/certificates/jobs/{job_id}")
    cert = status_res.json()["recipients"][0]
    code = cert["certificate_code"]
    assert code is not None

    # 3. Verify valid certificate
    verify_res = await async_client.get(f"/api/v1/certificates/verify/{code}")
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["is_valid"] is True
    assert data["certificate_code"] == code
    assert data["recipient_name"] == "Satoshi Nakamoto"
    assert data["event_name"] == "Cryptography & Zero Knowledge Systems"
    assert data["issuer_name"] == "Antigravity Research Labs"


@pytest.mark.asyncio
async def test_verify_invalid_code_returns_404(async_client: AsyncClient):
    verify_res = await async_client.get("/api/v1/certificates/verify/CERT-INVALID999")
    assert verify_res.status_code == 404
    assert "not authentic" in verify_res.json()["detail"].lower()
