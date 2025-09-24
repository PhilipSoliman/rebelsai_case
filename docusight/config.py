import re
from pathlib import Path

import torch
from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the RebelsAI app.
    Sensitive values are loaded from environment variables (.env file).
    Static paths are set here.
    """

    # Sensitive values (loaded from .env)
    DATABASE_URL: str
    DROPBOX_APP_KEY: str
    DROPBOX_APP_SECRET: str
    SESSION_SECRET_KEY: str

    # Base directory of the project
    PROJECT_DIR: Path = Path(__file__).resolve().parent.parent

    # Base directory for app-specific files
    APP_DIR: Path = PROJECT_DIR / "docusight"

    # Temporary directory for processing files
    TEMP_DIR: Path = APP_DIR / "temp"

    # Path to (dummy) client data folder (for testing / prototyping)
    DATA_DIR: Path = PROJECT_DIR / "data"

    # Upload directory (in dropbox, relative to root)
    UPLOAD_DIR: str = "/uploads"

    # Dropbox authentication redirect URI
    DROPBOX_REDIRECT_URI: str = "authentication/callback"

    # Dropbox account ID key in session
    DROPBOX_ACCOUNT_ID_SESSION_KEY: str = "dropbox_account_id"

    # File read chunk size (in bytes) when processing large files
    ZIP_FILE_READ_CHUNK_SIZE: int = 1024 * 1024  # 1 MB

    # Model name for classification
    CLASSIFICATION_MODEL_NAME: str = "nlptown/bert-base-multilingual-uncased-sentiment"

    # NOTE Some other models:
    # "nlptown/bert-base-multilingual-uncased-sentiment"
    # "tabularisai/multilingual-sentiment-analysis"
    # "DTAI-KULeuven/robbert-v2-dutch-sentiment"

    # GPU device
    GPU_DEVICE: int = 0 if torch.cuda.is_available() else -1

    # Classification batch size
    CLASSIFICATION_BATCH_SIZE: int = 16

    model_config = ConfigDict(env_file=".env")

    @field_validator("DROPBOX_APP_KEY", "DROPBOX_APP_SECRET")
    def not_placeholder(cls, v):
        if not re.fullmatch(r"[a-z0-9]{15}", v):
            raise ValueError(
                "Dropbox app keys must be 15-character lowercase alphanumeric strings. Current value: "
                + v
            )
        return v


# Create a single instance to import everywhere
settings = Settings()
