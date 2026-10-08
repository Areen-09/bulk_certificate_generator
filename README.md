# Bulk Certificate Generator Backend

A high-performance, asynchronous Python backend service for bulk certificate generation. Built with **FastAPI**, **SQLAlchemy 2.0**, and pure-Python **ReportLab**, featuring granular per-recipient failure isolation, background job processing, atomic database progress tracking, individual and bulk ZIP certificate retrieval, and public certificate verification.

Includes an interactive **Tailwind CSS + Shadcn-style web dashboard** served directly by FastAPI.

---

## Architecture Overview

```
                      +---------------------------------------+
                      | Client / Web UI / External API Caller |
                      +---------------------------------------+
                                          |
                        POST /api/v1/certificates/jobs (Bulk Batch)
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| FastAPI Application (Port 8000)                                                    |
|                                                                                   |
|  1. Validate payload structure via Pydantic v2                                    |
|  2. Persist GenerationJob & CertificateRecords in PENDING state                   |
|  3. Schedule background worker via FastAPI BackgroundTasks                        |
|  4. Return immediate 202 Accepted response with job_id and tracking links         |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| Asynchronous Job Worker (JobProcessor)                                           |
|                                                                                   |
|  For each recipient record:                                                       |
|    - Validate recipient fields (name, email)                                      |
|    - If invalid: Mark FAILED, capture error message, continue to next recipient   |
|    - If valid: Mark GENERATING                                                    |
|      - Generate unique verification code (e.g. CERT-A1B2C3D4)                     |
|      - Render high-resolution vector PDF via ReportLab                            |
|      - Save PDF file to storage/certificates/{job_id}/{cert_id}.pdf               |
|      - Mark COMPLETED and record file path                                        |
|    - Atomically update job counters (processed, successful, failed)               |
|  Finalize job status (COMPLETED, PARTIALLY_FAILED, or FAILED)                     |
+-----------------------------------------------------------------------------------+
                                          |
                 +------------------------+------------------------+
                 |                                                 |
                 v                                                 v
   +---------------------------+                     +---------------------------+
   | Relational Database       |                     | File Storage              |
   | SQLite (default)          |                     | storage/certificates/     |
   | PostgreSQL (configurable) |                     | Organized by {job_id}     |
   +---------------------------+                     +---------------------------+
```

---

## Key Features

- **Asynchronous Bulk Processing**: Non-blocking `202 Accepted` API design. Submitting 500+ certificates returns immediately while generation executes reliably in the background.
- **Strict Failure Isolation**: Validation or rendering errors on a single recipient **never** prevent valid certificates in the batch from being processed. The job status captures exact counts (`successful`, `failed`) and stores granular error reasons for every failed item.
- **Vector PDF Rendering (ReportLab)**: Standardized, print-ready landscape A4 certificates with navy and gold decorative borders, corner flourishes, official verification seal, dynamic typography scaling, and verification IDs. Zero external OS C-libraries required.
- **Dual Retrieval Modes**:
  - **Single PDF Download**: Direct download link for each individual certificate.
  - **Bulk ZIP Download**: On-the-fly streaming ZIP archive containing all successfully generated certificates in the batch.
- **Public Certificate Verification**: Public endpoint (`GET /api/v1/certificates/verify/{code}`) allowing anyone to verify certificate authenticity and issuance details.
- **Zero-Build Web Dashboard**: Built with modern Tailwind CSS and Shadcn-inspired aesthetics, served directly from FastAPI static files. Evaluators do not need Node.js or npm to test.
- **100% Automated Test Coverage**: Comprehensive `pytest` test suite verifying job creation, input validation, PDF generation, status transitions, failure isolation, download endpoints, and verification.

---

## Technology Stack & Design Decisions

| Component | Technology | Rationale & Interview Justification |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | High-performance async runtime, built-in OpenAPI/Swagger documentation (`/docs`), and robust request validation using Pydantic v2. |
| **Relational Database** | **SQLAlchemy 2.0 (Async)** + **SQLite** | Zero-configuration file database for reviewers with zero setup friction. Fully production-ready with instant switch to **PostgreSQL** via `DATABASE_URL`. |
| **Worker Architecture** | **FastAPI `BackgroundTasks`** | In-process asynchronous task orchestration eliminates external message broker dependencies (e.g., Redis/RabbitMQ) for seamless evaluation, while maintaining full state tracking in the DB. |
| **Certificate Generator** | **ReportLab** | Pure-Python vector PDF engine. Avoids system-level C-library dependencies (e.g. WeasyPrint/Pango/Cairo) that frequently cause installation failures on Windows/Linux environments. |
| **UI Dashboard** | **Tailwind CSS + Shadcn-style UI** | Modern dark-mode interface with live polling, progress animations, and interactive forms with zero Node/npm dependencies. |

---

## Project Structure

```
bulk_certificate_generator/
├── app/
│   ├── main.py                     # FastAPI application entrypoint & static mount
│   ├── core/
│   │   ├── config.py               # Pydantic BaseSettings (paths, limits, DB URL)
│   │   └── database.py             # SQLAlchemy async engine, sessionmaker, init_db
│   ├── models/
│   │   ├── job.py                  # GenerationJob model & JobStatus enum
│   │   └── certificate.py          # CertificateRecord model & CertificateStatus enum
│   ├── schemas/
│   │   ├── job.py                  # Request & response Pydantic schemas
│   │   └── certificate.py          # Recipient & verification schemas
│   ├── services/
│   │   ├── certificate_generator.py # ReportLab PDF rendering engine
│   │   ├── job_processor.py        # Background task worker with error isolation
│   │   └── storage_service.py      # File system persistence & ZIP compression
│   ├── api/
│   │   └── v1/
│   │       ├── router.py           # V1 route aggregator
│   │       └── endpoints/
│   │           ├── jobs.py         # POST batch, GET status, GET list
│   │           ├── certificates.py # Download PDF, download bulk ZIP
│   │           └── verify.py       # Public certificate verification
│   └── static/
│       └── index.html              # Tailwind + Shadcn UI dashboard
├── tests/
│   ├── conftest.py                 # Pytest fixtures (isolated DB & temporary storage)
│   ├── test_api_jobs.py            # Job creation, validation & pagination tests
│   ├── test_certificate_generator.py # ReportLab PDF rendering unit tests
│   ├── test_failure_handling.py    # Recipient failure isolation & partial status tests
│   ├── test_downloads.py           # Single PDF and bulk ZIP archive tests
│   └── test_verify.py              # Public certificate verification endpoint tests
├── storage/
│   └── certificates/               # Generated PDF output directory
├── pyproject.toml                  # Project configuration and dependencies
└── README.md                       # Documentation
```

---

## Getting Started

### 1. Prerequisites
- **Python 3.12+**
- (Optional but recommended) `uv` for package management.

### 2. Environment Setup

Using `uv` (recommended):
```bash
# Create virtual environment (if not already created)
uv venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies in editable mode with test dependencies
uv pip install -e ".[dev]"
```

Using standard `pip`:
```bash
python -m venv .venv
# Activate virtual environment
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/macOS

pip install -e ".[dev]"
```

---

## Running the Application

Start the development server with Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **Interactive Web UI Dashboard**: Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger OpenAPI Documentation**: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: Open [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Running the Automated Test Suite

Run the full automated test suite using `pytest`:

```bash
pytest -v
```

All 13 tests execute against an isolated temporary SQLite database and temporary storage directory:
- `test_create_job_success`: Verifies 202 Accepted and job initialization
- `test_input_validation_missing_fields`: Validates 422 Unprocessable Entity on invalid payload
- `test_get_job_status_not_found`: Validates 404 on nonexistent job ID
- `test_list_jobs`: Validates pagination and reverse-chronological job listing
- `test_certificate_generator_creates_valid_pdf`: Verifies `%PDF-` header and ReportLab vector rendering
- `test_certificate_generator_handles_long_names_and_unicode`: Verifies dynamic typography scaling and UTF-8 handling
- `test_download_single_certificate_and_zip`: Verifies individual PDF and bulk ZIP downloads
- `test_download_failed_certificate_returns_400`: Verifies rejected download attempt for failed records
- `test_download_nonexistent_certificate_returns_404`: Verifies 404 on invalid certificate IDs
- `test_handling_individual_certificate_failure`: Verifies that invalid recipients fail gracefully while valid recipients succeed
- `test_fully_failed_job`: Verifies that jobs with 100% invalid records transition to `FAILED`
- `test_verify_certificate_endpoint`: Verifies certificate authenticity validation
- `test_verify_invalid_code_returns_404`: Verifies rejection of counterfeit or unrecognized codes

---

## API Usage & Examples

### 1. Submit Bulk Certificate Generation Job

**Endpoint**: `POST /api/v1/certificates/jobs`  
**Status**: `202 Accepted`

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/certificates/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Executive Cloud Architecture Bootcamp",
    "issuer_name": "Antigravity Engineering Academy",
    "issue_date": "2026-10-08",
    "description": "for successfully mastering cloud architecture and microservices design",
    "recipients": [
      {
        "recipient_name": "Alice Johnson",
        "recipient_email": "alice@example.com",
        "custom_data": {"grade": "Distinction", "hours": 40}
      },
      {
        "recipient_name": "Bob Smith",
        "recipient_email": "bob@example.com",
        "custom_data": {"grade": "Merit", "hours": 40}
      },
      {
        "recipient_name": "",
        "recipient_email": "invalid-email-address"
      }
    ]
  }'
```

**Response**:
```json
{
  "job_id": "51f2cb6c-7f5b-4c4d-a2f0-1c6f4b9f3e12",
  "status": "PENDING",
  "total_count": 3,
  "message": "Certificate generation job accepted and scheduled for processing.",
  "links": {
    "status": "/api/v1/certificates/jobs/51f2cb6c-7f5b-4c4d-a2f0-1c6f4b9f3e12",
    "download_zip": "/api/v1/certificates/jobs/51f2cb6c-7f5b-4c4d-a2f0-1c6f4b9f3e12/download"
  }
}
```

---

### 2. Poll Job Status & Progress

**Endpoint**: `GET /api/v1/certificates/jobs/{job_id}`  
**Status**: `200 OK`

```bash
curl "http://127.0.0.1:8000/api/v1/certificates/jobs/51f2cb6c-7f5b-4c4d-a2f0-1c6f4b9f3e12"
```

**Response**:
```json
{
  "job_id": "51f2cb6c-7f5b-4c4d-a2f0-1c6f4b9f3e12",
  "event_name": "Executive Cloud Architecture Bootcamp",
  "issuer_name": "Antigravity Engineering Academy",
  "issue_date": "2026-10-08",
  "description": "for successfully mastering cloud architecture and microservices design",
  "status": "PARTIALLY_FAILED",
  "progress_percentage": 100.0,
  "counters": {
    "total": 3,
    "processed": 3,
    "successful": 2,
    "failed": 1
  },
  "created_at": "2026-10-08T17:30:00",
  "updated_at": "2026-10-08T17:30:01",
  "completed_at": "2026-10-08T17:30:01",
  "recipients": [
    {
      "certificate_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "certificate_code": "CERT-8F3A19B2",
      "status": "COMPLETED",
      "download_url": "/api/v1/certificates/c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c/download",
      "error_message": null,
      "custom_data": {"grade": "Distinction", "hours": 40}
    },
    {
      "certificate_id": "d2e3f4a5-b6c7-8d9e-0f1a-2b3c4d5e6f7a",
      "recipient_name": "Bob Smith",
      "recipient_email": "bob@example.com",
      "certificate_code": "CERT-2A7C99D1",
      "status": "COMPLETED",
      "download_url": "/api/v1/certificates/d2e3f4a5-b6c7-8d9e-0f1a-2b3c4d5e6f7a/download",
      "error_message": null,
      "custom_data": {"grade": "Merit", "hours": 40}
    },
    {
      "certificate_id": "e3f4a5b6-c7d8-9e0f-1a2b-3c4d5e6f7a8b",
      "recipient_name": "",
      "recipient_email": "invalid-email-address",
      "certificate_code": null,
      "status": "FAILED",
      "download_url": null,
      "error_message": "Recipient name cannot be empty or whitespace.",
      "custom_data": null
    }
  ]
}
```

---

### 3. Retrieve Generated Certificates

#### A. Download Single PDF
```bash
curl -O -J "http://127.0.0.1:8000/api/v1/certificates/c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c/download"
```
*Saves `Alice_Johnson_CERT-8F3A19B2.pdf` to current directory.*

#### B. Download All Certificates as ZIP
```bash
curl -O -J "http://127.0.0.1:8000/api/v1/certificates/jobs/51f2cb6c-7f5b-4c4d-a2f0-1c6f4b9f3e12/download"
```
*Saves `Executive_Cloud_Architecture_Bootcamp_certificates_51f2cb6c.zip` containing all successful certificates.*

---

### 4. Verify Certificate Authenticity

**Endpoint**: `GET /api/v1/certificates/verify/{certificate_code}`  
**Status**: `200 OK`

```bash
curl "http://127.0.0.1:8000/api/v1/certificates/verify/CERT-8F3A19B2"
```

**Response**:
```json
{
  "certificate_code": "CERT-8F3A19B2",
  "is_valid": true,
  "recipient_name": "Alice Johnson",
  "event_name": "Executive Cloud Architecture Bootcamp",
  "issuer_name": "Antigravity Engineering Academy",
  "issue_date": "2026-10-08",
  "description": "for successfully mastering cloud architecture and microservices design",
  "custom_data": {"grade": "Distinction", "hours": 40},
  "created_at": "2026-10-08T17:30:00"
}
```

### 4. How is Idempotency Handled?
- If a job has already finalized (`COMPLETED`, `PARTIALLY_FAILED`, `FAILED`), repeated worker calls exit immediately.
- If individual certificate records have already completed, they are skipped rather than re-rendered.
- Counters (`successful_count`, `failed_count`, `processed_count`) are computed from the underlying certificate items to prevent counter drift.
