from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from docusight.classifier_pipeline import setup_pipeline
from docusight.config import settings
from docusight.database import create_tables, drop_tables
from docusight.dropbox import cleanup_dropbox_files
from docusight.models import *  # ensures all models are declared before creating tables
from docusight.routers.authentication import router as authentication_router
from docusight.routers.classification import router as classification_router
from docusight.routers.insight import router as insight_router


# define lifespan event handler to create tables at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP #
    # check if dropbox app key and secret are set
    if (
        settings.DROPBOX_APP_KEY == "your_dropbox_app_key_here"
        or settings.DROPBOX_APP_SECRET == "your_dropbox_app_secret_here"
    ):
        raise ValueError(
            f"Dropbox app key and secret must be set in the {settings.PROJECT_DIR / '.env'} file."
        )

    # Create ORM tables
    await create_tables()

    # Initialize classification pipeline
    setup_pipeline(app)

    yield
    # SHUTDOWN #
    # Drop ORM tables
    await drop_tables()

    # Delete all files in Dropbox upload directory
    await cleanup_dropbox_files()


# Main application instance
app = FastAPI(
    title="📄👀 DocuSight API",
    description="API for document insights and classification",
    lifespan=lifespan,
)

# Add middleware for session management
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

# Connect routers containing endpoints
app.include_router(authentication_router)
app.include_router(insight_router)
app.include_router(classification_router)
