from fastapi import FastAPI

from docusight.routers.classification import router as classification_router
from docusight.routers.insight import router as insight_router

# main application instance
app = FastAPI(
    title="📄👀 DocuSight API",
    description="API for document insights and classification",
)

# connect routers containing endpoints
app.include_router(insight_router)
app.include_router(classification_router)