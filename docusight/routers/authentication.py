import urllib.parse
from typing import Optional

from dropbox import Dropbox
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from docusight.config import settings
from docusight.database import get_db
from docusight.dropbox import get_auth_flow
from docusight.models import User
from datetime import datetime

# NOTE: do not change this prefix as it is used in OAuth redirect URIs
router = APIRouter(
    prefix="/authentication",
    tags=["Authentication"],
)


# Response models
class DropboxAuthURLResponseModel(BaseModel):
    auth_url: str


class DropboxAuthCallbackResponseModel(BaseModel):
    user_id: int
    display_name: str
    email: str
    dropbox_account_id: str
    dropbox_access_token: str
    dropbox_refresh_token: str
    dropbox_access_token_expiration: Optional[datetime] = None


@router.get("/dropbox", response_model=DropboxAuthURLResponseModel)
async def dropbox_auth(request: Request):
    from fastapi.concurrency import run_in_threadpool

    print("Cookies:", dict(request.cookies))
    auth_flow = get_auth_flow(request.base_url, request.session)
    authorize_url = await run_in_threadpool(auth_flow.start)
    return DropboxAuthURLResponseModel(auth_url=authorize_url)


# NOTE: do not change this endpoint's name as it is used in OAuth redirect URIs
@router.get("/callback", response_model=DropboxAuthCallbackResponseModel)
async def dropbox_callback(
    request: Request,
    code: str,
    state: str,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    from fastapi.concurrency import run_in_threadpool

    try:
        print("Cookies:", dict(request.cookies))
        auth_flow = get_auth_flow(request.base_url, request.session)

        # Decode incoming OAuth parameters
        code_decoded = urllib.parse.unquote(code)
        state_decoded = urllib.parse.unquote(state)

        # Finish OAuth flow (blocking)
        oauth_result = await run_in_threadpool(
            auth_flow.finish,
            {"code": code_decoded, "state": state_decoded, "error": error},
        )

        # Get dropbox tokens
        access_token = oauth_result.access_token
        refresh_token = oauth_result.refresh_token

        # Create Dropbox client using access token
        dropbox_client = Dropbox(access_token)

        # Get user account info
        user_info = await run_in_threadpool(dropbox_client.users_get_current_account)
        display_name = user_info.name.display_name
        email = user_info.email
        account_id = user_info.account_id
        expires_at = oauth_result.expires_at if oauth_result.expires_at else None

        # Store account ID in session
        request.session[settings.DROPBOX_ACCOUNT_ID_SESSION_KEY] = account_id

        # Store user info in database
        user = User(
            display_name=display_name,
            email=email,
            dropbox_account_id=account_id,
            dropbox_access_token=access_token,
            dropbox_refresh_token=refresh_token,
            dropbox_access_token_expiration=expires_at,
            
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return DropboxAuthCallbackResponseModel(
            user_id=user.id,
            display_name=display_name,
            email=email,
            dropbox_account_id=account_id,
            dropbox_access_token=access_token,
            dropbox_refresh_token=refresh_token,
            dropbox_access_token_expiration=expires_at,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
