from fastapi import APIRouter, File, Request, UploadFile

from docusight.config import settings

router = APIRouter(
    prefix="/upload",
    tags=["File Upload"],
)


@router.post("/uploadfile/")
async def create_upload_file(request: Request, file: UploadFile = File(...)):
    dropbox_client = request.app.state.dropbox
    file_bytes = await file.read()
    fp = settings.UPLOAD_DIR / file.filename
    response = dropbox_client.files_upload(file_bytes, str(fp.as_posix()))
    return {
        "filename": file.filename,
        "dropbox_id": response.id,
        "dropbox_path": response.path_display,
    }
