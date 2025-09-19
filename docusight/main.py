from contextlib import asynccontextmanager

from fastapi import FastAPI

from docusight.database import create_tables, drop_tables
from docusight.models import *  # ensures all models are declared before creating tables
from docusight.routers.classification import router as classification_router
from docusight.routers.insight import router as insight_router
from docusight.routers.upload import router as upload_router
from docusight.config import settings, is_dropbox_token_set
from dropbox import Dropbox

# define lifespan event handler to create tables at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP #
    # check for dropbox token
    if not is_dropbox_token_set():
        raise RuntimeError("Dropbox access token is not set. Please update your .env file.")
    
    # instance of Dropbox client
    app.state.dropbox = Dropbox(settings.DROPBOX_ACCESS_TOKEN)

    # create ORM tables
    await create_tables()

    yield
    # SHUTDOWN #
    # delete dropbox client instance
    app.state.dropbox = None

    # drop ORM tables
    await drop_tables()


# main application instance
app = FastAPI(
    title="📄👀 DocuSight API",
    description="API for document insights and classification",
    lifespan=lifespan,
)

# connect routers containing endpoints
app.include_router(insight_router)
app.include_router(classification_router)
app.include_router(upload_router)
