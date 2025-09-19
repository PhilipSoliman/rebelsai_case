import os
import subprocess
import venv
from pathlib import Path

# Get the absolute path of the project directory
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))

# Default virtual environment directory
VENV_DIR = ".venv"

# Python executable within the virtual environment (corrected for linux/windows)
PYTHON_EXEC = (
    os.path.join(VENV_DIR, "Scripts", "python.exe")
    if os.name == "nt"
    else os.path.join(VENV_DIR, "bin", "python")
)


def create_virtual_environment():
    if not os.path.exists(VENV_DIR):
        venv.create(VENV_DIR, with_pip=True)
        print(f"✅ Created virtual environment '{VENV_DIR}'\n")
    else:
        print(f"Virtual environment '{VENV_DIR}' already exists")


def install_package():
    # upgrade pip
    subprocess.check_call([PYTHON_EXEC, "-m", "pip", "install", "--upgrade", "pip"])
    print("✅ Upgraded pip to latest version\n")

    # install local python package
    subprocess.check_call(
        [
            PYTHON_EXEC,
            "-m",
            "pip",
            "install",
            "-e",
            PROJECT_DIR,
        ]
    )
    print(f"✅ Installed local package in {PROJECT_DIR}\n")


def generate_default_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        print(f".env file already exists at {env_path}")
        return
    default_content = """
DATABASE_URL=sqlite+aiosqlite:///./rebelsai.db
DROPBOX_ACCESS_TOKEN=your_dropbox_token_here
"""
    env_path.write_text(default_content.strip())
    print(f"Default .env file created at {env_path}")


if __name__ == "__main__":
    create_virtual_environment()
    install_package()
    generate_default_env()