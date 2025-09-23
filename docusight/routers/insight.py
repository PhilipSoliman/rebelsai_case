from typing import Optional

from fastapi import APIRouter, Depends, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from docusight.database import get_db
from docusight.dropbox import get_dropbox_client, get_user
from docusight.file_utils import (
    add_zipped_folder_to_database,
    get_documents_in_folder,
    get_folder_by_path,
    get_subfolders_in_folder,
)
from docusight.logging import logger
from docusight.models import Document, Folder

router = APIRouter(
    prefix="/insight",
    tags=["Folder Insights"],
)


# response models & generators
class DocumentResponseModel(BaseModel):
    id: int
    path: str

    # original file meta
    folder_id: int
    filename: str
    size: int
    created: float
    modified: float

    # dropbox meta
    dropbox_path: Optional[str] = None
    plain_text_size: Optional[int] = None


def generate_document_response(document: Document) -> DocumentResponseModel:
    """
    Convert a Document ORM object to a DocumentResponseModel for API responses.

    Args:
        document (Document): The Document ORM instance.

    Returns:
        DocumentResponseModel: The response model for the document.
    """
    return DocumentResponseModel(
        id=document.id,
        path=document.path,
        folder_id=document.folder_id,
        filename=document.filename,
        size=document.size,
        created=document.created,
        modified=document.modified,
        dropbox_path=document.dropbox_path,
        plain_text_size=document.plain_text_size,
    )


class FolderResponseModel(BaseModel):
    id: int
    path: str
    name: str
    parent_id: Optional[int] = None
    documents: Optional[list[DocumentResponseModel]] = []
    subfolders: Optional[list["FolderResponseModel"]] = []


async def generate_folder_response(
    folder: Folder, db: AsyncSession
) -> FolderResponseModel:
    """
    Recursively generate a FolderResponseModel from a Folder ORM object, including documents and subfolders.

    Args:
        folder (Folder): The Folder ORM instance.
        db (AsyncSession): The database session.

    Returns:
        FolderResponseModel: The response model for the folder, including nested documents and subfolders.
    """
    documents = await get_documents_in_folder(folder, db)
    subfolders = await get_subfolders_in_folder(folder, db)
    return FolderResponseModel(
        id=folder.id,
        path=folder.path,
        name=folder.name,
        parent_id=folder.parent_id,
        documents=[generate_document_response(doc) for doc in documents],
        subfolders=[
            await generate_folder_response(subfolder, db) for subfolder in subfolders
        ],
    )


@router.post("/folder", response_model=FolderResponseModel)
async def analyze_folder(
    request: Request,
    zipped_folder: UploadFile,
    drill: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a zipped folder by extracting its contents, adding them to the database, and uploading files to Dropbox.

    - If the folder already exists in the database, returns its structure and metadata.
    - Otherwise, extracts the zip, populates the database, uploads files to Dropbox, and returns the new folder structure.

    Args:
        request (Request): FastAPI request object.
        zipped_folder (UploadFile): The uploaded zipped folder (.zip file).
        drill (bool, optional): Whether to recursively add subfolders. Defaults to True.
        db (AsyncSession): Database session dependency.

    Returns:
        FolderResponseModel: The folder structure and metadata, including documents and subfolders.
    """
    # get current user
    user = await get_user(db, request.session)

    # get top level folder name from zip file
    folder_name = zipped_folder.filename.replace(".zip", "")

    # Check if folder already exists in the database
    existing_folder = await get_folder_by_path(str(folder_name), db, user)
    if existing_folder:
        logger.info(f"Folder {folder_name} already already exists in the database.")
        return await generate_folder_response(existing_folder, db)

    # add folder to database (& upload file contents to dropbox)
    dropbox_client = await get_dropbox_client(user)
    folder = await add_zipped_folder_to_database(
        zipped_folder=zipped_folder,
        db=db,
        dropbox_client=dropbox_client,
        user=user,
        drill=drill,
    )

    # generate response
    response = await generate_folder_response(folder, db)
    logger.info(f"Added folder {folder_name} to the database.")

    # Commit the transaction and refresh the folder instance
    await db.commit()
    await db.refresh(folder)

    return response


# TODO (Nice-to-have): Add endpoint for folder deletion

# TODO (Nice-to-have): Add endpoint for folder update

# TODO (Nice-to-have): Add endpoint for document deletion

# TODO (Nice-to-have): Add endpoint for document update
