import os
from pathlib import Path
from typing import Optional

from sqlalchemy.future import select
from sqlalchemy.orm import Session, selectinload

from docusight.models import Document, Folder


async def add_folder_to_database(folder_path: str, db: Session, drill: bool) -> Folder:
    """Add a folder and its documents to the database.
    Args:
        folder (Folder): Folder object to be added.
        db (Session): Database session.
        drill (bool, optional): Whether to recursively add subfolders. Defaults to True.
    """

    root_folder = await add_folder_to_database_recursive(folder_path, db, drill)
    return root_folder


async def add_folder_to_database_recursive(
    current_path: str,
    db: Session,
    drill: bool,
    parent_folder: Optional[Folder] = None,
) -> Folder:
    folder = Folder(
        path=str(current_path),
        parent_id=parent_folder.id if parent_folder else None,
    )
    db.add(folder)
    await db.flush()
    for file in os.listdir(current_path):
        file_path = Path(current_path) / file
        if file_path.is_file():
            stats = file_path.stat()
            document = Document(
                folder=folder,
                filename=file,
                path=str(file_path),
                size=stats.st_size,
                created=stats.st_ctime,
                modified=stats.st_mtime,
            )
            db.add(document)

    # Add subfolders recursively
    if drill:
        for subfolder_name in os.listdir(current_path):
            subfolder_path = Path(current_path) / subfolder_name
            if subfolder_path.is_dir():
                _ = await add_folder_to_database_recursive(
                    str(subfolder_path), db, drill, folder
                )
    return folder


async def get_folder_by_path(path: str, db: Session) -> Optional[Folder]:
    result = await db.execute(
        select(Folder)
        .options(selectinload(Folder.documents), selectinload(Folder.subfolders))
        .where(Folder.path == str(path))
    )
    return result.scalars().first()


async def get_documents_in_folder(folder: Folder, db: Session) -> list[Document]:
    result = await db.execute(select(Document).where(Document.folder_id == folder.id))
    return result.scalars().all()


async def get_subfolders_in_folder(folder: Folder, db: Session) -> list[Folder]:
    result = await db.execute(select(Folder).where(Folder.parent_id == folder.id))
    return result.scalars().all()
