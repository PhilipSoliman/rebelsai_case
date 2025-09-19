from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from docusight.config import settings
from docusight.database import get_db
from docusight.file_utils import add_folder_to_database, get_folder_by_path
from docusight.models import Document, Folder

router = APIRouter(
    prefix="/insight",
    tags=["Folder Insights"],
)


# response models & generators
class DocumentResponseModel(BaseModel):
    id: int
    path: str
    folder_id: int
    filename: str
    size: int
    created: float
    modified: float


def generate_document_response(document: Document) -> DocumentResponseModel:
    return DocumentResponseModel(
        id=document.id,
        path=document.path,
        folder_id=document.folder_id,
        filename=document.filename,
        size=document.size,
        created=document.created,
        modified=document.modified,
    )


class FolderResponseModel(BaseModel):
    id: int
    path: str
    parent_id: Optional[int] = None
    documents: Optional[list[DocumentResponseModel]] = []
    subfolders: Optional[list["FolderResponseModel"]] = []


async def generate_folder_response(folder: Folder, db: Session) -> FolderResponseModel:
    subfolders_result = await db.execute(
        select(Folder).where(Folder.parent_id == folder.id)
    )
    subfolders = subfolders_result.scalars().all()
    documents_result = await db.execute(
        select(Document).where(Document.folder_id == folder.id)
    )
    documents = documents_result.scalars().all()
    return FolderResponseModel(
        id=folder.id,
        path=folder.path,
        parent_id=folder.parent_id,
        documents=[generate_document_response(doc) for doc in documents],
        subfolders=[
            await generate_folder_response(subfolder, db) for subfolder in subfolders
        ],
    )


# API Endpoints
@router.post("/folder", response_model=FolderResponseModel)
async def post_folder(
    folder_path: str = None, drill: bool = True, db: Session = Depends(get_db)
):
    """
    Add Folder and its documents to database. If no folder_path is provided, it defaults to the CLIENT_DATA_DIR.
    If drill is True, it will recursively add any subfolders and their documents as well.

    Args:
        folder_path (str, optional): Path to the folder to be added. Defaults to None.
        drill (bool, optional): Whether to recursively add subfolders. Defaults to True.
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        dict: Information about the added folder.
    """
    # Determine the folder path
    path = Path(folder_path) if folder_path else settings.CLIENT_DATA_DIR

    # Check if folder already exists in the database
    existing_folder = await get_folder_by_path(str(path), db)
    if existing_folder:
        return await generate_folder_response(
            existing_folder, message="Folder already exists in the database."
        )

    # add folder to database
    folder = await add_folder_to_database(str(path), db, drill)

    # generate response
    response = await generate_folder_response(folder, db)

    # Commit the transaction and refresh the folder instance
    await db.commit()
    await db.refresh(folder)

    return response


# @router.get("/metadata")
# async def get_insight(folder_path: str = None):
#     """
#     Get metadata insights of files in the specified folder.
#     If no folder_path is provided, it defaults to the CLIENT_DATA_DIR.
#     """

#     path = Path(folder_path) if folder_path else settings.CLIENT_DATA_DIR
#     insights = await analyze_folder(path)
#     return insights
