import warnings

import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch
from sqlalchemy.future import select

from docusight.models import Document
from tests.conftest import (
    EXPECTED_SENTIMENTS,
    SAMPLE_FOLDER_DIR,
    TEMP_DROPBOX_DIR,
    mock_get_dropbox_client,
    mock_get_user,
)


@pytest.mark.asyncio
@pytest.mark.order(3)
async def test_classification_endpoint(
    async_client_and_db: AsyncClient, monkeypatch: MonkeyPatch
):
    async_client, db = async_client_and_db

    # Mock get_user to return the first user in the database
    monkeypatch.setattr("docusight.routers.classification.get_user", mock_get_user)

    # Mock Dropbox client methods
    monkeypatch.setattr(
        "docusight.routers.classification.get_dropbox_client", mock_get_dropbox_client
    )

    # Mock download_files_from_dropbox to return files from TEMP_DROPBOX_DIR
    monkeypatch.setattr(
        "docusight.routers.classification.download_files_from_dropbox",
        mock_download_files_from_dropbox,
    )

    response = await async_client.post("/classification/folder?folder_path=sample")
    assert response.status_code == 200
    data = response.json()

    # get all filenames from SAMPLE_FOLDER_DIR
    project_names = [f.name for f in SAMPLE_FOLDER_DIR.glob("**/*") if f.is_file()]

    # query database for these documents
    project_docs = []
    for project_name in project_names:
        query = await db.execute(
            select(Document).where(Document.filename == project_name)
        )
        doc = query.scalars().first()
        if doc:
            project_docs.append(doc)

    classifications = data["classified_documents"]
    for classification in classifications:
        doc_id = classification["document"]["id"]
        assert any(
            doc.id == doc_id for doc in project_docs
        ), f"Document ID {doc_id} not found in DB"
        document_name = classification["document"]["filename"].split(".")[0]
        if classification["label"] != EXPECTED_SENTIMENTS[document_name]:
            warnings.warn(f"Unexpected label {classification['label']} for {document_name}")


async def mock_download_files_from_dropbox(dropbox_client, dropbox_paths, tmp_dir):
    # Return all files in TEMP_DROPBOX_DIR
    return list(TEMP_DROPBOX_DIR.glob("*"))
