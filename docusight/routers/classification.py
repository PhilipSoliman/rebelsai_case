import os
import shutil
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from transformers import Pipeline

from docusight.config import settings
from docusight.database import get_db
from docusight.dropbox import get_dropbox_client, get_user
from docusight.file_utils import (
    download_files_from_dropbox,
    generate_tmp_dir,
    get_documents_in_folder,
    get_folder_by_path,
)
from docusight.logging import logger
from docusight.models import Classification, Folder
from docusight.routers.insight import DocumentResponseModel, generate_document_response

router = APIRouter(
    prefix="/classification",
    tags=["Classification"],
)


# Response models
class DocumentClassificationResponseModel(BaseModel):
    id: int
    document_id: int
    label: str
    score: float
    document: DocumentResponseModel


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
    Classifies sentiment for all documents in a specified folder and its subfolders.

    Downloads unclassified documents from Dropbox, runs batch sentiment analysis using the configured Hugging Face pipeline,
    stores results in the database, and returns all classified documents (including previously classified ones).

    Args:
        request (Request): FastAPI request object.
        folder_path (str): Relative path to the folder to classify.
        db (AsyncSession): Database session dependency.

    Returns:
        FolderClassificationResponseModel: Contains folder path and list of classified documents with sentiment labels and scores.
    """
    # create temporary directory for downloads
    user = await get_user(db, request.session)
    tmp_dir = generate_tmp_dir(user)

    try:
        # obtain folder and documents
        folder: Folder = await get_folder_by_path(folder_path, db, user)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        # get both classified and unclassified documents
        unclassified_documents = await get_documents_in_folder(
            folder, db, drill=True, classified=False
        )
        classified_documents = await get_documents_in_folder(
            folder, db, drill=True, classified=True
        )
        if unclassified_documents == [] and classified_documents == []:
            raise HTTPException(
                status_code=400, detail="No documents in folder to classify"
            )

        # download unclassified documents from dropbox
        dropbox_client = await get_dropbox_client(user)
        dropbox_paths = [
            doc.dropbox_path for doc in unclassified_documents if doc.dropbox_path
        ]
        os.makedirs(tmp_dir, exist_ok=True)
        local_paths: list[Path] = await download_files_from_dropbox(
            dropbox_client, dropbox_paths, tmp_dir
        )

        # classify each document
        classifier: Pipeline = request.app.state.sentiment_classifier
        classifications = []
        batch_size = settings.CLASSIFICATION_BATCH_SIZE
        for i in range(0, len(local_paths), batch_size):
            # read batch of files
            batch_paths = local_paths[i : i + batch_size]
            batch_texts = []
            for doc_path in batch_paths:
                async with aiofiles.open(
                    doc_path, "r", encoding="utf-8", errors="replace"
                ) as f:
                    text = await f.read()
                    batch_texts.append(text)

            # classify batch
            batch_results = await classify_batch(classifier, batch_texts)

            # map results back to documents
            batch_docs = unclassified_documents[i : i + batch_size]
            for doc, res in zip(batch_docs, batch_results):
                label = res["label"]
                score = res["score"]

                # Save to DB
                classification = Classification(
                    user_id=user.id, document=doc, label=label, score=score
                )
                db.add(classification)

                # store classification for response
                classifications.append(classification)

        # Remove temporary directory
        await run_in_threadpool(shutil.rmtree, tmp_dir)

        # Commit the transaction and refresh the folder instance
        await db.commit()
        for classification in classifications:
            await db.refresh(classification)

        # Add already classified documents to response
        result = await db.execute(
            select(Classification).where(
                Classification.document_id.in_([doc.id for doc in classified_documents])
            )
        )
        classifications.extend(result.scalars().all())

        # Prepare responses
        classification_responses = []
        for classification in classifications:
            classification_response = DocumentClassificationResponseModel(
                id=classification.id,
                document_id=classification.document_id,
                label=classification.label,
                score=classification.score,
                document=generate_document_response(classification.document),
            )
            classification_responses.append(classification_response)

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
    """
    Runs batch sentiment classification using the provided Hugging Face pipeline.
    Executes in a threadpool for performance.

    Args:
        classifier (Pipeline): Hugging Face sentiment analysis pipeline.
        texts (list[str]): List of document texts to classify.

    Returns:
        list[dict]: List of classification results, each with 'label' and 'score'.
    """
    # classify in threadpool
    result = await run_in_threadpool(
        classifier, texts, batch_size=settings.CLASSIFICATION_BATCH_SIZE
    )

    # Normalize labels to "Positive", "Negative", "Neutral" (supports various model outputs)
    for res in result:
        label = res["label"].lower()

        # Handle cases like "4 stars", "very positive", etc.
        if label.endswith(" stars"):
            stars = int(label.split(" ")[0])
            if stars <= 2:
                res["label"] = "Negative"
            elif stars == 3:
                res["label"] = "Neutral"
            else:
                res["label"] = "Positive"

        # Handle cases like "very negative", "positive", "neutral", etc.
        if label in ["very  negative", "negative"]:
            res["label"] = "Negative"
        elif label in ["neutral"]:
            res["label"] = "Neutral"
        elif label in ["positive", "very  positive"]:
            res["label"] = "Positive"

    return result
