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

    # Directories
    PROJECT_DIR: Path = Path(__file__).resolve().parent.parent
    APP_DIR: Path = PROJECT_DIR / "docusight"
    TEMP_DIR: Path = APP_DIR / "temp"
    DATA_DIR: Path = PROJECT_DIR / "data"
    UPLOAD_DIR: str = "/uploads"

    # Load settings from .env file
    model_config = ConfigDict(env_file=APP_DIR / ".env")

    @field_validator("DROPBOX_APP_KEY", "DROPBOX_APP_SECRET")
    def not_placeholder(cls, v):
        if not re.fullmatch(r"[a-z0-9]{15}", v):
            raise ValueError(
                "Dropbox app keys must be 15-character lowercase alphanumeric strings. Current value: "
                + v
            )
        return v

    # Sensitive values (loaded from .env)
    DATABASE_URL: str
    DROPBOX_APP_KEY: str
    DROPBOX_APP_SECRET: str
    SESSION_SECRET_KEY: str

    # Classification pipeline settings
    PYTORCH_CUDA_VERSION: str
    CLASSIFICATION_MODEL_NAME: str
    GPU_DEVICE: int = 0 if torch.cuda.is_available() else -1
    CLASSIFICATION_BATCH_SIZE: int = 16

    # Dropbox authentication redirect URI
    DROPBOX_REDIRECT_URI: str = "authentication/callback"

    # Dropbox account ID key in session
    DROPBOX_ACCOUNT_ID_SESSION_KEY: str = "dropbox_account_id"

    # File read chunk size (in bytes) when processing large zipped archives
    ZIP_FILE_READ_CHUNK_SIZE: int = 1024 * 1024  # 1 MB


# Create a single instance to import everywhere
settings = Settings()
