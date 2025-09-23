import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from docusight.database import create_tables, drop_tables, get_db
from docusight.dropbox import cleanup_dropbox_files
from docusight.main import app


@pytest_asyncio.fixture
async def async_client_and_db():
    # Code run before tests start
    await create_tables()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Code run during before each test
        gen = get_db()
        db = await gen.__anext__()
        yield ac, db  # input for each test

        # Code run after each test
        await db.close()

    # Code run after all tests finish
    await cleanup_dropbox_files()
    await drop_tables()  # drop all tables
