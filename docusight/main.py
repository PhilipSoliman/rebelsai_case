from contextlib import asynccontextmanager

from fastapi import FastAPI

from docusight.database import create_tables, drop_tables
from docusight.models import *  # ensures all models are declared before creating tables
from docusight.routers.classification import router as classification_router
from docusight.routers.insight import router as insight_router


# define lifespan event handler to create tables at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup code
    await create_tables()
    yield
    # shutdown code
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
