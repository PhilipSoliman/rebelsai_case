import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Optional

import aiofiles
from dropbox import Dropbox, files
from fastapi import HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from docusight.config import settings
from docusight.logging import logger
from docusight.models import Document, Folder


async def add_zipped_folder_to_database(
    request: Request,
    zipped_folder: UploadFile,
    db: AsyncSession,
    drill: bool,
) -> Folder:
    """
    Extracts a zipped folder, adds its contents to the database, uploads files to Dropbox, and cleans up temporary files.

    Args:
        request (Request): FastAPI request object.
        zipped_folder (UploadFile): The uploaded zipped folder (.zip file).
        db (AsyncSession): Database session.
        drill (bool): Whether to recursively add subfolders.

    Returns:
        Folder: The Folder ORM instance added to the database.
    """
    tmp_dir = Path(settings.TEMP_DIR) / settings.DEFAULT_USER_NAME
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_zipped_folder_path = Path(tmp_dir) / zipped_folder.filename
    tmp_client_dir = tmp_zipped_folder_path.with_suffix("")  # folder name without .zip

    await write_zip_in_chunks(zipped_folder, tmp_zipped_folder_path)
    await run_in_threadpool(extract_zip, tmp_zipped_folder_path)
    await delete_zipfile(tmp_zipped_folder_path)

    file_paths = []
    folder = await add_folder_to_database(
        tmp_client_dir, tmp_dir, db, drill, file_paths=file_paths
    )

    if file_paths:
        dropbox_paths = await upload_files_to_dropbox(request, file_paths, tmp_dir)

    for relative_path, dropbox_path in dropbox_paths.items():
        document = await get_document_by_path(str(relative_path), db)
        if document:
            document.dropbox_path = dropbox_path
            db.add(document)

    await run_in_threadpool(shutil.rmtree, tmp_client_dir)
    return folder


async def delete_zipfile(zip_path: Path):
    """
    Asynchronously deletes a zip file from disk.

    Args:
        zip_path (Path): Path to the zip file to delete.
    """
    if zip_path.exists():
        await run_in_threadpool(zip_path.unlink)


async def write_zip_in_chunks(upload_file: UploadFile, dest_path: Path):
    """
    Asynchronously writes an uploaded zip file to disk in chunks.

    Args:
        upload_file (UploadFile): The uploaded zip file.
        dest_path (Path): Destination path to write the file.
    """
    with open(dest_path, "wb") as f:
        while True:
            chunk = await upload_file.read(settings.FILE_READ_CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)


def extract_zip(tmp_zipped_folder_path: Path):
    """
    Extracts a zip file to a directory with the same name (without .zip).

    Args:
        tmp_zipped_folder_path (Path): Path to the zip file to extract.
    """
    with zipfile.ZipFile(tmp_zipped_folder_path, "r") as zip_ref:
        zip_ref.extractall(tmp_zipped_folder_path.parent)


async def delete_extracted_files(tmp_zipped_folder_path: Path):
    """
    Asynchronously deletes all files and subdirectories in the extracted folder.

    Args:
        tmp_zipped_folder_path (Path): Path to the extracted folder.
    """
    for root, dirs, files in os.walk(tmp_zipped_folder_path, topdown=False):
        for name in files:
            await run_in_threadpool(os.remove, os.path.join(root, name))
        for name in dirs:
            await run_in_threadpool(os.rmdir, os.path.join(root, name))


async def add_folder_to_database(
    current_dir: Path,
    tmp_dir: Path,
    db: AsyncSession,
    drill: bool,
    file_paths: list[Path],
    parent_folder: Optional[Folder] = None,
) -> Folder:
    """
    Recursively adds a folder and its documents to the database.

    Args:
        current_dir (Path): Path to the current folder.
        tmp_dir (Path): Base temp directory.
        db (AsyncSession): Database session.
        drill (bool): Whether to recursively add subfolders.
        file_paths (list[Path]): List to collect file paths for upload.
        parent_folder (Optional[Folder]): Parent folder ORM instance.

    Returns:
        Folder: The Folder ORM instance added to the database.
    """
    folder = Folder(
        path=str(current_dir.relative_to(tmp_dir)),
        name=current_dir.name,
        parent_id=parent_folder.id if parent_folder else None,
    )
    db.add(folder)
    await db.flush()
    for file in os.listdir(current_dir):
        file_path = Path(current_dir) / file
        if file_path.is_file():
            file_paths.append(file_path)
            stats = file_path.stat()
            document = Document(
                folder=folder,
                filename=file,
                path=str(file_path.relative_to(tmp_dir)),
                dropbox_path=None,  # to be updated after upload
                size=stats.st_size,
                created=stats.st_ctime,
                modified=stats.st_mtime,
            )
            db.add(document)

    # Add subfolders recursively
    if drill:
        for subfolder_name in os.listdir(current_dir):
            subfolder_path = Path(current_dir) / subfolder_name
            if subfolder_path.is_dir():
                _ = await add_folder_to_database(
                    subfolder_path,
                    tmp_dir,
                    db,
                    drill,
                    file_paths=file_paths,
                    parent_folder=folder,
                )
    return folder


async def upload_files_to_dropbox(
    request: Request, file_paths: list[Path], tmp_dir: Path
) -> tuple[dict, files.UploadSessionFinishBatchResult]:
    """
    Uploads multiple files to Dropbox using upload sessions, chunking each file and finishing all sessions in a batch.

    Args:
        request (Request): FastAPI request object.
        file_paths (list[Path]): List of file paths to upload.
        tmp_dir (Path): Base temp directory.

    Returns:
        tuple[dict, files.UploadSessionFinishBatchResult]:
            - dict mapping relative file paths to Dropbox paths
            - Dropbox batch result object
    """
    dropbox_client: Dropbox = request.app.state.dropbox

    try:
        dropbox_paths = {}
        entries: list[files.UploadSessionFinishArg] = []
        batch_start_result = await run_in_threadpool(
            dropbox_client.files_upload_session_start_batch,
            len(file_paths),
            files.UploadSessionType.sequential,
        )

        # get session ids
        if len(batch_start_result.session_ids) != len(file_paths):
            raise HTTPException(
                status_code=500,
                detail="Dropbox did not return session IDs for all files",
            )

        # Loop over files and upload each one in chunks
        for file_path, session_id in zip(file_paths, batch_start_result.session_ids):
            # Relative filepath
            relative_path = file_path.relative_to(tmp_dir)

            # Generate unique file ID and path
            file_id = str(uuid.uuid4())
            file_ext = (
                "." + file_path.name.split(".")[-1] if "." in file_path.name else ""
            )
            dropbox_filename = f"{file_id}{file_ext}"
            dropbox_path = (
                f"{settings.UPLOAD_DIR}/{settings.DEFAULT_USER_NAME}/{dropbox_filename}"
            )

            # Append the rest of the chunks using aiofiles for async file I/O
            cursor = files.UploadSessionCursor(session_id=session_id, offset=0)
            async with aiofiles.open(file_path, "rb") as file:
                while True:
                    chunk = await file.read(settings.FILE_READ_CHUNK_SIZE)
                    if not chunk:
                        await run_in_threadpool(
                            dropbox_client.files_upload_session_append_v2,
                            b"",
                            cursor,
                            close=True,
                        )
                        break
                    await run_in_threadpool(
                        dropbox_client.files_upload_session_append_v2,
                        chunk,
                        cursor,
                    )
                    # offset += len(chunk)
                    cursor.offset += len(chunk)

            # Save entry for batch finish
            commit = files.CommitInfo(path=dropbox_path)
            finish_arg = files.UploadSessionFinishArg(cursor=cursor, commit=commit)
            entries.append(finish_arg)

            # Save metadata for response
            dropbox_paths[str(relative_path)] = dropbox_path

        # Finish all sessions in one batch
        finish_batch_result: files.UploadSessionFinishBatchResult = (
            await run_in_threadpool(
                dropbox_client.files_upload_session_finish_batch_v2,
                entries,
            )
        )

    except Exception as e:
        logger.error(f"Error uploading file(s) to Dropbox: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to upload file(s) to Dropbox"
        )

    # check for any failed uploads
    failures = []
    for entry in finish_batch_result.entries:
        if entry.is_failure():
            logger.error(f"Failed to upload file to Dropbox: {entry}")
            failures.append(entry)
    if failures:
        raise HTTPException(
            status_code=500, detail="Failed to upload one or more files to Dropbox"
        )

    return dropbox_paths


async def get_folder_by_segments(
    segments: list[str], db: AsyncSession
) -> Optional[Folder]:
    """
    Retrieves a Folder ORM instance by its path segments from the database.

    Args:
        segments (list[str]): List of path segments representing the folder hierarchy.
        db (AsyncSession): Database session.

    Returns:
        Optional[Folder]: The Folder ORM instance, or None if not found.
    """
    parent_id = None
    folder = None
    for segment in segments:
        # only search parent folder
        query = select(Folder).where(Folder.parent_id == parent_id)

        # search for the folder by name
        query = query.where(Folder.name == segment)
        # if parent_id is not None:
        #     query = query.where(Folder.parent_id == parent_id)
        result = await db.execute(query)
        folder = result.scalars().first()
        if not folder:
            return None
        parent_id = folder.id
    return folder


async def get_folder_by_path(path: str, db: AsyncSession) -> Optional[Folder]:
    """
    Retrieves a Folder ORM instance by its path from the database.

    Args:
        path (str): Relative path of the folder.
        db (AsyncSession): Database session.

    Returns:
        Optional[Folder]: The Folder ORM instance, or None if not found.
    """
    # Traverse the folder hierarchy using path segments
    segments = Path(path).parts
    return await get_folder_by_segments(segments, db)


async def get_document_by_path(path: str, db: AsyncSession) -> Optional[Document]:
    """
    Retrieves a Document ORM instance by its path from the database.

    Args:
        path (str): Relative path of the document.
        db (AsyncSession): Database session.

    Returns:
        Optional[Document]: The Document ORM instance, or None if not found.
    """
    segments = Path(path).parts
    if len(segments) < 2:
        raise HTTPException(status_code=400, detail="Invalid document path")

    # get parent folder of document
    *folder_segments, filename = segments
    folder = await get_folder_by_segments(folder_segments, db)
    if not folder:
        raise HTTPException(status_code=404, detail="Document folder not found")

    # get document by filename and folder_id
    result = await db.execute(
        select(Document).where(
            Document.folder_id == folder.id, Document.filename == filename
        )
    )
    return result.scalars().first()


async def get_documents_in_folder(folder: Folder, db: AsyncSession) -> list[Document]:
    """
    Retrieves all Document ORM instances in a given folder.

    Args:
        folder (Folder): The Folder ORM instance.
        db (AsyncSession): Database session.

    Returns:
        list[Document]: List of Document ORM instances in the folder.
    """
    result = await db.execute(select(Document).where(Document.folder_id == folder.id))
    return result.scalars().all()


async def get_subfolders_in_folder(folder: Folder, db: AsyncSession) -> list[Folder]:
    """
    Retrieves all subfolder ORM instances for a given folder.

    Args:
        folder (Folder): The Folder ORM instance.
        db (AsyncSession): Database session.

    Returns:
        list[Folder]: List of subfolder ORM instances.
    """
    result = await db.execute(select(Folder).where(Folder.parent_id == folder.id))
    return result.scalars().all()
