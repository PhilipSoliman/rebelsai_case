from dropbox import Dropbox
from fastapi import APIRouter, HTTPException, Request

from docusight.dropbox import get_auth_flow

prefix = "/authentication"
router = APIRouter(
    prefix=prefix,
    tags=["Authentication"],
)

@router.get("/dropbox")
async def dropbox_auth(request: Request):
    redirect_uri = str(request.base_url) + prefix + "/dropbox"
    auth_flow = get_auth_flow(redirect_uri)
    authorize_url = auth_flow.start()
    return {"auth_url": authorize_url}

@router.get("/callback")
async def dropbox_callback(request: Request, code: str):
    redirect_uri = str(request.base_url) + prefix + "/dropbox"
    auth_flow = get_auth_flow(redirect_uri)
    try:
        oauth_result = auth_flow.finish(code)
        access_token = oauth_result.access_token
        request.app.state.dropbox = Dropbox(access_token)
        return {"access_token": access_token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))