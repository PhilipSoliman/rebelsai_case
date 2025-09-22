from dropbox import Dropbox
from dropbox.oauth import DropboxOAuth2Flow
from fastapi import FastAPI
from httpcore import request

from docusight.config import is_dropbox_token_set, settings


# def setup_dropbox_client(app: FastAPI) -> Dropbox:
#     if not is_dropbox_token_set():
#         raise RuntimeError(
#             "Dropbox access token is not set. Please update your .env file."
#         )
#     app.state.dropbox = Dropbox(settings.DROPBOX_ACCESS_TOKEN)


def cleanup_dropbox_files(app: FastAPI):
    if hasattr(request.app.state, "dropbox"):
        dropbox_client: Dropbox = app.state.dropbox
        try:
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


def get_auth_flow(redirect_uri: str) -> DropboxOAuth2Flow:
    return DropboxOAuth2Flow(
        settings.DROPBOX_APP_KEY,
        settings.DROPBOX_APP_SECRET,
        redirect_uri,
        session={},  # Not used in stateless API, but required
        csrf_token_session_key="dropbox-auth-csrf-token",
    )
