import os
import zipfile
from pathlib import Path
from shutil import rmtree

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

from docusight.classifier_pipeline import setup_pipeline
from docusight.config import settings
from docusight.database import create_tables, drop_tables, get_db
from docusight.main import app
from docusight.models import User

TEMP_MOCK_USER = "Mock User"
TEMP_DROPBOX_DIR = settings.TEMP_DIR / "mock_dropbox" / "uploads"
SAMPLE_FOLDER_DIR = settings.DATA_DIR / "sample"
ZIPPED_FOLDER_PATH = settings.PROJECT_DIR / "tests" / "sample.zip"
EXPECTED_SENTIMENTS = {
    "Project 1": "Positive",
    "Project 2": "Positive",
    "Project 3": "Negative",
    "Project 4": "Positive",
    "Project 5": "Negative",
}


@pytest_asyncio.fixture(scope="session")
async def async_client_and_db():
    # Code run before tests start
    await create_tables()
    zip_sample_folder()
    setup_pipeline(app)

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
    delete_zipped_sample()
    await drop_tables()


def zip_sample_folder():
    if SAMPLE_FOLDER_DIR.exists():
        with zipfile.ZipFile(ZIPPED_FOLDER_PATH, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(SAMPLE_FOLDER_DIR):
                # Skip the root directory itself
                if Path(root) == SAMPLE_FOLDER_DIR:
                    continue
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(SAMPLE_FOLDER_DIR.parent)
                    zipf.write(file_path, arcname)


def delete_zipped_sample():
    if ZIPPED_FOLDER_PATH.exists():
        ZIPPED_FOLDER_PATH.unlink()


async def mock_get_dropbox_client(user):
    pass


async def mock_get_user(db, session):
    result = await db.execute(select(User).limit(1))
    user = result.scalars().first()
    if user:
        return user
    raise Exception("No user found in DB for mock_get_user")
