from contextlib import asynccontextmanager

from fastapi import FastAPI

from docusight.classifier_pipeline import setup_pipeline
from docusight.database import create_tables, drop_tables
from docusight.dropbox import cleanup_dropbox_files, setup_dropbox_client
from docusight.models import *  # ensures all models are declared before creating tables
from docusight.routers.authentication import router as authentication_router
from docusight.routers.classification import router as classification_router
from docusight.routers.insight import router as insight_router


# define lifespan event handler to create tables at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP #
    await create_tables()

    setup_pipeline(app)

    yield
    # SHUTDOWN #
    # drop ORM tables
    await drop_tables()

    # Delete all files in Dropbox upload directory
    cleanup_dropbox_files(app)

    # delete dropbox client instance
    app.state.dropbox = None


# main application instance
app = FastAPI(
    title="📄👀 DocuSight API",
    description="API for document insights and classification",
    lifespan=lifespan,
)

# connect routers containing endpoints
app.include_router(authentication_router)
app.include_router(insight_router)
app.include_router(classification_router)
