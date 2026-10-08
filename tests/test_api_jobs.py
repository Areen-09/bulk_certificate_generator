import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_job_success(async_client: AsyncClient):
    payload = {
        "event_name": "Modern Cloud DevOps Workshop",
        "issuer_name": "DevOps Institute",
        "issue_date": "2026-10-08",
        "description": "for successfully mastering CI/CD pipelines",
        "recipients": [
            {"recipient_name": "John Doe", "recipient_email": "john@example.com"},
            {"recipient_name": "Jane Smith", "recipient_email": "jane@example.com"},
        ],
    }

    response = await async_client.post("/api/v1/certificates/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()

    assert "job_id" in data
    assert data["status"] == "PENDING"
    assert data["total_count"] == 2
    assert "links" in data
    assert "status" in data["links"]


@pytest.mark.asyncio
async def test_input_validation_missing_fields(async_client: AsyncClient):
    # Missing event_name
    bad_payload = {
        "recipients": [{"recipient_name": "Bob"}],
    }
    response = await async_client.post("/api/v1/certificates/jobs", json=bad_payload)
    assert response.status_code == 422

    # Empty recipients list
    bad_payload2 = {
        "event_name": "AI Workshop",
        "recipients": [],
    }
    response2 = await async_client.post("/api/v1/certificates/jobs", json=bad_payload2)
    assert response2.status_code == 422


@pytest.mark.asyncio
async def test_get_job_status_not_found(async_client: AsyncClient):
    response = await async_client.get("/api/v1/certificates/jobs/non-existent-uuid-12345")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_jobs(async_client: AsyncClient):
    # Create a job first
    payload = {
        "event_name": "Python Async Internals",
        "recipients": [{"recipient_name": "Guido"}],
    }
    await async_client.post("/api/v1/certificates/jobs", json=payload)

    # List jobs
    response = await async_client.get("/api/v1/certificates/jobs?limit=10")
    assert response.status_code == 200
    jobs = response.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    assert jobs[0]["event_name"] == "Python Async Internals"
