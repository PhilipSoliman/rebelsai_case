from pathlib import Path

import torch
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the RebelsAI app.
    Sensitive values are loaded from environment variables (.env file).
    Static paths are set here.
    """

    # Sensitive values (loaded from .env)
    DATABASE_URL: str
    DROPBOX_ACCESS_TOKEN: str

    # Base directory of the project
    PROJECT_DIR: Path = Path(__file__).resolve().parent.parent

    # Base directory for app-specific files
    APP_DIR: Path = PROJECT_DIR / "docusight"

    # Temporary directory for processing files
    TEMP_DIR: Path = APP_DIR / "temp"

    # Path to (dummy) client data folder (for testing / prototyping)
    CLIENT_DATA_DIR: Path = PROJECT_DIR / "client_data"

    # Path to (dummy) client zipped folder
    CLIENT_ZIPPED_FOLDER: Path = CLIENT_DATA_DIR.with_suffix(".zip")

    # Upload directory (in dropbox, relative to root)
    UPLOAD_DIR: str = "/uploads"

    # User name place holder TODO: implement user management
    DEFAULT_USER_NAME: str = "default_user"

    # File read chunk size (in bytes) when processing large files
    ZIP_FILE_READ_CHUNK_SIZE: int = 1024 * 1024  # 1 MB

    # Model name for classification TODO: Find dutch sentiment analysis model
    CLASSIFICATION_MODEL_NAME: str = "DTAI-KULeuven/robbert-v2-dutch-sentiment"

    # GPU device
    GPU_DEVICE: int = 0 if torch.cuda.is_available() else -1

    # Classification batch size
    CLASSIFICATION_BATCH_SIZE: int = 16

    class Config:
        env_file = "../.env"  # relative to config.py


# Create a single instance to import everywhere
settings = Settings()


# Check dropbox token
def is_dropbox_token_set() -> bool:
    token = settings.DROPBOX_ACCESS_TOKEN
    return bool(token) and token != "your_dropbox_token_here"
