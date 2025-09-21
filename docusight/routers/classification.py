import os
import shutil
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from transformers import Pipeline

from docusight.config import settings
from docusight.database import get_db
from docusight.file_utils import (
    download_files_from_dropbox,
    get_documents_in_folder,
    get_folder_by_path,
)
from docusight.logging import logger
from docusight.models import Classification, Document, Folder

router = APIRouter(
    prefix="/classification",
    tags=["Classification"],
)


# Response models & generators
class DocumentClassificationResponseModel(BaseModel):
    id: int
    document_id: int
    label: str
    score: float


class FolderClassificationResponseModel(BaseModel):
    folder_path: str
    classified_documents: list[DocumentClassificationResponseModel]


@router.post("/folder", response_model=FolderClassificationResponseModel)
async def classify_folder(
    request: Request,
    folder_path: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Classify sentiment of all files in a folder.
    Assumes file text has already been extracted into DB (File.text_content).
    Stores results in ClassificationResult table.
    """
    # create temporary directory for downloads
    download_folder_id = str(uuid.uuid4())
    tmp_dir = (
            Path(settings.TEMP_DIR) / settings.DEFAULT_USER_NAME / download_folder_id
        )
    
    try:
        # obtain folder and documents
        folder: Folder = await get_folder_by_path(folder_path, db)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        documents: list[Document] = await get_documents_in_folder(
            folder, db, drill=True
        )

        # download documents from dropbox
        dropbox_paths = [doc.dropbox_path for doc in documents if doc.dropbox_path]
        if not dropbox_paths:
            raise HTTPException(
                status_code=400, detail="No documents with Dropbox paths found"
            )
 
        os.makedirs(tmp_dir, exist_ok=True)
        local_paths: list[Path] = await download_files_from_dropbox(
            request.app.state.dropbox, dropbox_paths, tmp_dir
        )

        # classify each document
        classifier: Pipeline = request.app.state.sentiment_classifier
        classification_responses = []
        batch_size = settings.CLASSIFICATION_BATCH_SIZE
        for i in range(0, len(local_paths), batch_size):
            # read batch of files
            batch_paths = local_paths[i : i + batch_size]
            batch_texts = []
            for doc_path in batch_paths:
                async with aiofiles.open(doc_path, "r", encoding="utf-8", errors="replace") as f:
                    text = await f.read()
                    batch_texts.append(text)

            # classify batch
            batch_results = await classify_batch(classifier, batch_texts)

            # map results back to documents
            batch_docs = documents[i : i + batch_size]
            for doc, res in zip(batch_docs, batch_results):
                label = res["label"]
                score = res["score"]

                # Save to DB
                classification = Classification(document=doc, label=label, score=score)
                db.add(classification)

                # Prepare response
                classification_response = DocumentClassificationResponseModel(
                    id=classification.id,
                    document_id=doc.id,
                    label=label,
                    score=score,
                )
                classification_responses.append(classification_response)

        # Remove temporary directory
        await run_in_threadpool(shutil.rmtree, tmp_dir)

        # Commit the transaction and refresh the folder instance
        await db.commit()
        await db.refresh(folder)

        return FolderClassificationResponseModel(
            folder_path=folder.path,
            classified_documents=classification_responses,
        )

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        if tmp_dir.exists():
            await run_in_threadpool(shutil.rmtree, tmp_dir)
        raise HTTPException(status_code=500, detail="Sentiment classification failed")


async def classify_batch(classifier: Pipeline, texts: list[str]):
    """Run batch classification in threadpool."""
    return await run_in_threadpool(classifier, texts)
