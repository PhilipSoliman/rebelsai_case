from docusight.config import settings
from dropbox import Dropbox

def cleanup_dropbox_files(app):
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
        print(f"Error deleting Dropbox files in {settings.UPLOAD_DIR.as_posix()}: {e}")
