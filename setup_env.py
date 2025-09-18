import os
import subprocess
import venv

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

if __name__ == "__main__":
    create_virtual_environment()
    install_package()