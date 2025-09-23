from dropbox import Dropbox
from dropbox.exceptions import AuthError
from dropbox.oauth import DropboxOAuth2Flow
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from docusight.config import settings
from docusight.database import get_db
from docusight.logging import logger
from docusight.models import User


def get_auth_flow(base_url: str, session: dict) -> DropboxOAuth2Flow:
    return DropboxOAuth2Flow(
        consumer_key=settings.DROPBOX_APP_KEY,
        consumer_secret=settings.DROPBOX_APP_SECRET,
        redirect_uri=str(base_url) + settings.DROPBOX_REDIRECT_URI,
        session=session,
        csrf_token_session_key="dropbox-auth-csrf-token",
        token_access_type="offline",
    )


async def get_dropbox_client(user: User) -> Dropbox:
    """
    Return a Dropbox client for the current user using the access token stored in session.
    Assumes session['dropbox_access_token'] is set after OAuth2 callback.
    """
    try:
        dbx = Dropbox(
            oauth2_access_token=user.dropbox_access_token,
            oauth2_access_token_expiration=user.dropbox_access_token_expiration,
            oauth2_refresh_token=user.dropbox_refresh_token,
            app_key=settings.DROPBOX_APP_KEY,
            app_secret=settings.DROPBOX_APP_SECRET,
        )
        await run_in_threadpool(dbx.users_get_current_account)
    except AuthError as e:
        logger.error(f"Invalid or expired Dropbox access token: {e}.")
        raise HTTPException(
            status_code=401, detail=f"Invalid or expired Dropbox access token: {e}."
        )
    return dbx


async def get_user(db: AsyncSession, session: dict) -> User:
    """
    Retrieve the user ID from the database using the session.
    """
    query = select(User).where(
        User.dropbox_account_id == get_dropbox_account_id(session)
    )
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        logger.error("No user found in database.")
        raise HTTPException(status_code=404, detail="User not found.")
    return user


def get_dropbox_account_id(session: dict) -> str:
    """
    Retrieve the user ID (via Dropbox account ID) from the session.
    """
    dropbox_account_id = session.get(settings.DROPBOX_ACCOUNT_ID_SESSION_KEY)
    if not dropbox_account_id:
        logger.error("No Dropbox account ID found in session.")
        raise HTTPException(
            status_code=401, detail="No Dropbox account ID found in session."
        )
    return dropbox_account_id


async def cleanup_dropbox_files():
    db = await get_db().__anext__()
    result = await db.execute(select(User))
    users: list[User] = result.scalars().all()
    for user in users:
        try:
            dropbox_client = await get_dropbox_client(user)

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
            logger.error(f"Error cleaning up Dropbox files for user {user}: {e}")
