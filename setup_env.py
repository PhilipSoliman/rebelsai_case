import os
import re
import secrets
import subprocess
import sys
import venv
from pathlib import Path

# Get the absolute path of the project directory
PROJECT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))

APP_DIR = PROJECT_DIR / "docusight"

# Default virtual environment directory
VENV_DIR = ".venv"

# Dictionary to hold environment variables
ENV_PATH = APP_DIR / ".env"
ENV_VARS = {}

# CUDA versions supported by PyTorch
CUDA_VERSIONS = ["cu118", "cu126", "cu128"]

# Python executable within the virtual environment (corrected for linux/windows)
use_global_python = "--use-global-python" in sys.argv

if use_global_python:
    PYTHON_EXEC = sys.executable
else:
    PYTHON_EXEC = (
        os.path.join(VENV_DIR, "Scripts", "python.exe")
        if os.name == "nt"
        else os.path.join(VENV_DIR, "bin", "python3")
    )


def create_virtual_environment():
    if not use_global_python:
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

    # Parse command-line args
    app_key = None
    app_secret = None
    for i, arg in enumerate(sys.argv):
        if arg == "--app-key" and i + 1 < len(sys.argv):
            app_key = sys.argv[i + 1]
        if arg == "--app-secret" and i + 1 < len(sys.argv):
            app_secret = sys.argv[i + 1]

    # Read existing .env if present
    if ENV_PATH.exists():
        with ENV_PATH.open("r") as f:
            for line in f:
                if line.strip() and not line.strip().startswith("#"):
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        ENV_VARS[k] = v

    # Set or update required variables
    ENV_VARS["DATABASE_URL"] = ENV_VARS.get(
        "DATABASE_URL", "sqlite+aiosqlite:///./rebelsai.db"
    )
    ENV_VARS["DROPBOX_APP_KEY"] = (
        app_key
        if app_key is not None
        else ENV_VARS.get("DROPBOX_APP_KEY", "your_dropbox_app_key_here")
    )
    ENV_VARS["DROPBOX_APP_SECRET"] = (
        app_secret
        if app_secret is not None
        else ENV_VARS.get("DROPBOX_APP_SECRET", "your_dropbox_app_secret_here")
    )
    ENV_VARS["SESSION_SECRET_KEY"] = ENV_VARS.get(
        "SESSION_SECRET_KEY", secrets.token_urlsafe(32)
    )
    ENV_VARS["PYTORCH_CUDA_VERSION"] = ENV_VARS.get("PYTORCH_CUDA_VERSION", None)
    ENV_VARS["CLASSIFICATION_MODEL_NAME"] = ENV_VARS.get(
        "CLASSIFICATION_MODEL_NAME", "nlptown/bert-base-multilingual-uncased-sentiment"
    )


def install_torch():
    # Find CUDA version
    cuda_version = _get_cuda_version()

    # check if the detected CUDA version matches the one in ENV_VARS (if set)
    if ENV_VARS["PYTORCH_CUDA_VERSION"] is not None:
        assert ENV_VARS["PYTORCH_CUDA_VERSION"] == cuda_version, (
            f"Environment variable PYTORCH_CUDA_VERSION={ENV_VARS['PYTORCH_CUDA_VERSION']} "
            f"does not match detected CUDA version {cuda_version}."
        )

    # update env vars with the detected CUDA version if not set
    ENV_VARS["PYTORCH_CUDA_VERSION"] = cuda_version

    # update ENV_VARS with the actual CUDA version used (or if the CPU is used)
    ENV_VARS["PYTORCH_CUDA_VERSION"] = cuda_version
    cuda_used = False
    print(f"Detected CUDA version: {cuda_version}")
    if cuda_version in CUDA_VERSIONS:
        cuda_used = True
        torch_url = f"https://download.pytorch.org/whl/{cuda_version}"
    else:
        torch_url = "https://download.pytorch.org/whl/cpu"

    # install PyTorch with or without CUDA support
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
        print(
            "CUDA not found. If you want to speed up some calculations in this project, please install CUDA. Continuing without CUDA."
        )
        return ""


if __name__ == "__main__":
    create_virtual_environment()
    install_package()
    generate_default_env()
    install_torch()

    # Write updated .env
    with ENV_PATH.open("w") as f:
        for k, v in ENV_VARS.items():
            f.write(f"{k}={v}\n")
    print(f"✅ .env file updated at {ENV_PATH}")
