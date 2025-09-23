import uuid
from pathlib import Path

import aiofiles
import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch
from sqlalchemy.future import select

from docusight.models import Document, User
from tests.conftest import TEMP_DROPBOX_DIR, ZIPPED_FOLDER_PATH


@pytest.mark.asyncio
@pytest.mark.order(2)
async def test_insight_endpoint(
    async_client_and_db: AsyncClient, monkeypatch: MonkeyPatch
):
    async_client, db = async_client_and_db

    # Mock get_user to return the first user in the database
    monkeypatch.setattr("docusight.routers.insight.get_user", mock_get_user)

    # Mock Dropbox client methods
    monkeypatch.setattr(
        "docusight.routers.insight.get_dropbox_client", mock_get_dropbox_client
    )

    # Mock Dropbox upload function
    monkeypatch.setattr(
        "docusight.file_utils.upload_files_to_dropbox", mock_upload_files_to_dropbox
    )

    # Prepare zipped folder
    with ZIPPED_FOLDER_PATH.open("rb") as f:
        files = {"zipped_folder": ("client_data.zip", f, "application/zip")}
        response = await async_client.post("/insight/folder?drill=true", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "documents" in data
    assert "subfolders" in data

    # Assert number of documents in DB matches number of files in TEMP_DROPBOX_DIR
    user = await mock_get_user(db, None)
    docs_result = await db.execute(select(Document).where(Document.user_id == user.id))
    db_docs = docs_result.fetchall()
    dropbox_files = list(TEMP_DROPBOX_DIR.glob("*"))
    assert len(db_docs) == len(dropbox_files)


async def mock_get_user(db, session):
    result = await db.execute(select(User).limit(1))
    user = result.scalars().first()
    if user:
        return user
    raise Exception("No user found in DB for mock_get_user")


async def mock_get_dropbox_client(user):
    return None


async def mock_upload_files_to_dropbox(dropbox_client, file_paths, tmp_dir):
    # Simulate storing files locally and return fake dropbox paths
    dropbox_paths = {}
    for file_path in file_paths:
        # Copy file to a local 'mock_dropbox' directory
        TEMP_DROPBOX_DIR.mkdir(parents=True, exist_ok=True)
        file_id = str(uuid.uuid4())
        file_ext = "." + file_path.name.split(".")[-1] if "." in file_path.name else ""
        mock_dropbox_filename = f"{file_id}{file_ext}"
        dest = TEMP_DROPBOX_DIR / mock_dropbox_filename
        async with (
            aiofiles.open(file_path, "rb") as src,
            aiofiles.open(dest, "wb") as dst,
        ):
            content = await src.read()
            await dst.write(content)
        dropbox_paths[file_path.relative_to(tmp_dir)] = str(dest)
    return dropbox_paths
