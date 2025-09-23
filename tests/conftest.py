from pathlib import Path
from shutil import rmtree

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from docusight.config import settings
from docusight.database import create_tables, drop_tables, get_db
from docusight.main import app

TEMP_MOCK_USER = "Mock User"
TEMP_DROPBOX_DIR = Path(settings.TEMP_DIR) / "mock_dropbox" / "uploads"
ZIPPED_FOLDER_PATH = settings.PROJECT_DIR / "tests" / "client_data.zip"


@pytest_asyncio.fixture(scope="session")
async def async_client_and_db():
    # Code run before tests start
    await create_tables()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Code run before each test (setup for each test)
        gen = get_db()
        db = await gen.__anext__()
        yield ac, db  # input for each test

        # Code run after each test
        await db.close()

    # Code run after all tests using this fixture have finished
    rmtree(settings.TEMP_DIR, ignore_errors=True)
    rmtree(TEMP_DROPBOX_DIR, ignore_errors=True)
    await drop_tables()
