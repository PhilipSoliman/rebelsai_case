from pathlib import Path

class Settings:
    """
    Configuration settings for the RebelsAI app.
    Can be extended for database URLs, API keys, upload paths, etc.
    """
    # Base directory of the project
    PROJECT_DIR: Path = Path(__file__).resolve().parent.parent

    # Base directory for app-specific files
    APP_DIR: Path = PROJECT_DIR / "docusight"

    # Path to (dummy) client data folder (for testing / prototyping)
    CLIENT_DATA_DIR: Path = PROJECT_DIR / "client_data"

    # Example of future config placeholders
    DATABASE_URL: str = "sqlite:///./rebelsai.db"

# Create a single instance to import everywhere
settings = Settings()