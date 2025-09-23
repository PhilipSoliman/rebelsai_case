from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from pytest import MonkeyPatch
from sqlalchemy.future import select

from docusight.dropbox import DropboxOAuth2Flow
from docusight.models import User
from docusight.routers.authentication import Dropbox
from tests.conftest import TEMP_MOCK_USER


@pytest.mark.asyncio
@pytest.mark.order(1)
async def test_authentication_endpoint(
    async_client_and_db: AsyncClient, monkeypatch: MonkeyPatch
):
    async_client, db = async_client_and_db

    # Mock DropboxOAuth2Flow and Dropbox methods
    monkeypatch.setattr(DropboxOAuth2Flow, "start", mock_start)
    monkeypatch.setattr(DropboxOAuth2Flow, "finish", mock_finish)
    monkeypatch.setattr(Dropbox, "__init__", mock_dropbox_init)
    monkeypatch.setattr(
        Dropbox, "users_get_current_account", mock_users_get_current_account
    )

    # Test /authentication/dropbox
    response = await async_client.get("/authentication/dropbox")
    assert response.status_code == 200
    assert "auth_url" in response.json()

    # Test /callback
    response = await async_client.get(
        "/authentication/callback", params={"code": "fake_code", "state": "fake_state"}
    )
    assert response.status_code == 200
    assert "user_id" in response.json()
    assert "display_name" in response.json()
    assert "email" in response.json()
    assert "dropbox_account_id" in response.json()
    assert "dropbox_access_token" in response.json()
    assert "dropbox_refresh_token" in response.json()
    assert "dropbox_access_token_expiration" in response.json()

    # check if user in database
    result = await db.execute(
        select(User).where(User.dropbox_account_id == "mock_account_id")
    )
    user = result.scalars().first()
    assert user is not None


class MockOAuthResult:
    access_token = "mock_access_token"
    account_id = "mock_account_id"
    user_id = "mock_user_id"
    refresh_token = "mock_refresh_token"
    expires_at = datetime.now() + timedelta(hours=1)
    scope = "mock_scope"


def mock_start(self):
    return "https://mocked-dropbox-auth-url"


def mock_finish(self, params):
    return MockOAuthResult()


class MockUserInfo:
    name = type("Name", (), {"display_name": TEMP_MOCK_USER})
    email = "mockuser@example.com"
    account_id = "mock_account_id"


def mock_dropbox_init(self, access_token):
    pass  # Do nothing


def mock_users_get_current_account(self):
    return MockUserInfo()
