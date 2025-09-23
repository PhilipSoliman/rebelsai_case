import os
import re
import subprocess
import venv
from pathlib import Path
import secrets

# Get the absolute path of the project directory
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))

# Default virtual environment directory
VENV_DIR = ".venv"

# CUDA versions supported by PyTorch
CUDA_VERSIONS = ["cu118", "cu126", "cu128"]

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


def install_torch():
    # install PyTorch with or without CUDA support
    cuda_version = _get_cuda_version()
    cuda_used = False
    print(f"Detected CUDA version: {cuda_version}")
    if cuda_version in CUDA_VERSIONS:
        cuda_used = True
        torch_url = f"https://download.pytorch.org/whl/{cuda_version}"
    else:
        torch_url = "https://download.pytorch.org/whl/cpu"

    subprocess.check_call(
        [
            PYTHON_EXEC,
            "-m",
            "pip",
            "install",
            "torch",
            "--index-url",
            torch_url,
        ]
    )
    print(
        f"✅ Installed PyTorch {'with CUDA support' if cuda_used else 'without CUDA support'}\n"
    )


def _get_cuda_version():
    try:
        output = subprocess.check_output(["nvcc", "--version"]).decode()
        for line in output.split("\n"):
            if "release" in line:
                match = re.search(r"release (\d+)\.(\d+)", line)
                if match:
                    major, minor = match.groups()
                    version = f"{major}{minor}"
                    return f"cu{version}"
                else:
                    raise ValueError("Could not parse CUDA version from nvcc output.")
    except FileNotFoundError:
        input(
            "CUDA not found. If you want to speed up some calculations in this project, please install CUDA. Press Enter to continue without CUDA."
        )
        return ""


def generate_default_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        print(f".env file already exists at {env_path}")
        return
    default_content = f"""
DATABASE_URL=sqlite+aiosqlite:///./rebelsai.db
DROPBOX_APP_KEY=your_dropbox_app_key_here
DROPBOX_APP_SECRET=your_dropbox_app_secret_here
SESSION_SECRET_KEY={secrets.token_urlsafe(32)}
"""
    env_path.write_text(default_content.strip())
    print(f"Default .env file created at {env_path}")


if __name__ == "__main__":
    create_virtual_environment()
    install_package()
    install_torch()
    generate_default_env()
