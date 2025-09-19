from pathlib import Path

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

    # Path to (dummy) client data folder (for testing / prototyping)
    CLIENT_DATA_DIR: Path = PROJECT_DIR / "client_data"

    # Upload directory (in dropbox, relative to root)
    UPLOAD_DIR: Path = Path("/uploads")

    class Config:
        env_file = "../.env"  # relative to config.py

# Create a single instance to import everywhere
settings = Settings()

# Check dropbox token
def is_dropbox_token_set() -> bool:
    token = settings.DROPBOX_ACCESS_TOKEN
    return bool(token) and token != "your_dropbox_token_here"