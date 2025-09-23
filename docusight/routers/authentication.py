import urllib.parse
from typing import Optional

from dropbox import Dropbox
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from docusight.dropbox import get_auth_flow

# NOTE: do not change this prefix as it is used in OAuth redirect URIs
router = APIRouter(
    prefix="/authentication",
    tags=["Authentication"],
)


# Response models
class DropboxAuthURLResponseModel(BaseModel):
    auth_url: str


class DropboxAuthCallbackResponseModel(BaseModel):
    display_name: str
    email: str
    account_id: str
    access_token: str
    refresh_token: str


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
    request: Request, code: str, state: str, error: Optional[str] = None
):
    from fastapi.concurrency import run_in_threadpool

    try:
        print("Cookies:", dict(request.cookies))
        auth_flow = get_auth_flow(request.base_url, request.session)

        # decode incoming OAuth parameters
        code_decoded = urllib.parse.unquote(code)
        state_decoded = urllib.parse.unquote(state)

        # finish OAuth flow (blocking)
        oauth_result = await run_in_threadpool(
            auth_flow.finish,
            {"code": code_decoded, "state": state_decoded, "error": error},
        )

        # create Dropbox client using access token
        access_token = oauth_result.access_token
        dropbox_client = Dropbox(access_token)
        request.app.state.dropbox = dropbox_client  # TODO: make dropbox client per user, do not store in app state

        # store refresh token for long-term access
        refresh_token = oauth_result.refresh_token

        # get user account info (blocking)
        user_info = await run_in_threadpool(dropbox_client.users_get_current_account)
        display_name = user_info.name.display_name
        email = user_info.email
        account_id = user_info.account_id

        return DropboxAuthCallbackResponseModel(
            display_name=display_name,
            email=email,
            account_id=account_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
