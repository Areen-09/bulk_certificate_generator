import os
import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core import database
from app.core.config import settings
from app.main import app


@pytest.fixture(scope="session")
def temp_storage_dir():
    """Creates a temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_cert_storage_")
    orig_storage = settings.STORAGE_DIR
    settings.STORAGE_DIR = Path(temp_dir)
    yield Path(temp_dir)
    # Cleanup
    settings.STORAGE_DIR = orig_storage
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture(scope="function")
async def setup_test_db(temp_storage_dir) -> AsyncGenerator[None, None]:
    """Sets up an isolated test SQLite database for each test run."""
    temp_db_file = temp_storage_dir / f"test_{os.urandom(4).hex()}.db"
    test_db_url = f"sqlite+aiosqlite:///{temp_db_file}"
    original_db_url = settings.DATABASE_URL

    # Point global configuration and database to test DB
    settings.DATABASE_URL = test_db_url
    database.set_database_url(test_db_url)

    # Initialize all database tables
    await database.init_db()

    yield

    # Teardown
    await database.engine.dispose()
    settings.DATABASE_URL = original_db_url
    database.set_database_url(original_db_url)
    if temp_db_file.exists():
        temp_db_file.unlink()


@pytest_asyncio.fixture(scope="function")
async def async_client(setup_test_db) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client for testing FastAPI API routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
