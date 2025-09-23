from dropbox import Dropbox
from dropbox.oauth import DropboxOAuth2Flow
from fastapi import FastAPI

from docusight.config import settings


def cleanup_dropbox_files(app: FastAPI):
    try:
        dropbox_client = app.state.dropbox  # TODO: implement per-user dropbox client

        # List all files in the upload directory
        res = dropbox_client.files_list_folder(settings.UPLOAD_DIR)
        for entry in res.entries:
            if hasattr(entry, "path_display"):
                dropbox_client.files_delete_v2(entry.path_display)
        # If there are more files, continue listing and deleting
        while res.has_more:
            res = dropbox_client.files_list_folder_continue(res.cursor)
            for entry in res.entries:
                if hasattr(entry, "path_display"):
                    dropbox_client.files_delete_v2(entry.path_display)
    except Exception as e:
        print(f"Error deleting Dropbox files in {settings.UPLOAD_DIR}: {e}")


def get_auth_flow(base_url: str, session: dict) -> DropboxOAuth2Flow:
    return DropboxOAuth2Flow(
        consumer_key=settings.DROPBOX_APP_KEY,
        consumer_secret=settings.DROPBOX_APP_SECRET,
        redirect_uri=str(base_url) + settings.DROPBOX_REDIRECT_URI,
        session=session,
        csrf_token_session_key="dropbox-auth-csrf-token",
        token_access_type="offline",
    )


def get_dropbox_client(session: dict) -> Dropbox:
    # TODO: implement per-user dropbox client using stored access tokens
    pass


def get_user_id_from_session(session: dict) -> str:
    # TODO: implement user retrieval from session
    pass
