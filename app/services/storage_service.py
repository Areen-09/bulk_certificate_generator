import io
import zipfile
from pathlib import Path
from typing import List, Tuple

from app.core.config import settings


class StorageService:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or settings.STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, job_id: str) -> Path:
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def get_certificate_path(self, job_id: str, certificate_id: str) -> Path:
        return self.get_job_dir(job_id) / f"{certificate_id}.pdf"

    def save_certificate_pdf(self, job_id: str, certificate_id: str, pdf_bytes: bytes) -> str:
        """Saves PDF bytes and returns relative file path."""
        target_path = self.get_certificate_path(job_id, certificate_id)
        with open(target_path, "wb") as f:
            f.write(pdf_bytes)
        return str(target_path.relative_to(settings.BASE_DIR))

    def get_file_bytes(self, relative_path: str) -> bytes | None:
        """Reads file bytes from relative path."""
        full_path = settings.BASE_DIR / relative_path
        if full_path.exists() and full_path.is_file():
            return full_path.read_bytes()
        return None

    def create_job_zip(self, job_id: str, certificates: List[Tuple[str, str]]) -> bytes:
        """
        Creates an in-memory ZIP archive of generated certificates.
        certificates: List of (relative_file_path, suggested_filename)
        """
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for rel_path, filename in certificates:
                full_path = settings.BASE_DIR / rel_path
                if full_path.exists() and full_path.is_file():
                    zip_file.write(full_path, arcname=filename)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()


storage_service = StorageService()
