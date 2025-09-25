# RebelsAI Case Study – DocuSight (Intelligent Document Management API)

This project is a **FastAPI-based backend service** that provides intelligent document management endpoints.
It can scan a (zipped) folder of documents, extract metadata, and perform document classification / sentiment analysis.

---

## Features
* **General Features**

  * API built with FastAPI.
  * Asynchronous database operations using SQLAlchemy + aiosqlite.
  * User authentication via Dropbox OAuth2.
  * Folder scanning and metadata extraction.
  * Document conversion to plain text.
  * Dropbox's Python SDK integration for blob storage.
  * Document classification using Hugging Face Transformers and PyTorch+CUDA.
  * User management; tied to folders, documents, and classifications.
  * CI setup with GitHub Actions.
  * Containerized deployment with Docker (including GPU support).
  * Tests endpoints with PyTest and HTTPX.

* **Dropbox Authentication Endpoint**

  * Implements OAuth2 flow for Dropbox authentication.
  * Uses `dropbox` Python SDK to handle OAuth2 and token management.
  * Stores user tokens securely in the database.

* **Folder Insight Endpoint**

  * Counts documents in a folder (including subdirectories).
  * Extracts metadata such as file name, size, creation date, etc.
  * Saves metadata into database.
  * Converts input files into plain *.txt files and uploads them to user's Dropbox as blob storage.

* **Document Classification Endpoint**

  * Classifies documents using:
    * Hugging Face Transformers pipeline for NLP tasks.
    * PyTorch + CUDA for ML model inference with either CPU or in parallel if GPU is configured (see [Setting up PyTorch+CUDA](#setting-up-pytorchcuda)).
  * Stores classification results in the database.
---

## Tech Stack

* **Python 3.9+**
* **FastAPI** – web framework for building APIs.
* **SQLAlchemy + aiosqlite** – ORM for relational, asynchronous database (SQLite).
* **Uvicorn** – ASGI server to run the app.
* **PyTorch+CUDA** – for running ML models on GPU.
* [**Hugging Face Transformers**](https://github.com/huggingface/transformers?tab=readme-ov-file) – Dutch NLP and sentiment analysis. Supported models: 
  * [DTAI-KULeuven/robbert-v2-dutch-sentiment](https://huggingface.co/DTAI-KULeuven/robbert-v2-dutch-sentiment)  (default).
  * [nlptown/bert-base-multilingual-uncased-sentiment](https://huggingface.co/nlptown/bert-base-multilingual-uncased-sentiment)
  * [tabularisai/multilingual-sentiment-analysis](https://huggingface.co/tabularisai/multilingual-sentiment-analysis).
---

## Requirements
* Python 3.9+
* Dropbox account (for OAuth2 authentication and blob storage)
* [Dropbox App](https://www.dropbox.com/developers/apps?_tk=pilot_lp&_ad=topbar4&_camp=myapps). Either create your own or use an existing/provided one with:
  * App Key and App Secret; 
  * Redirect URI to `http://<host_ip>:8000/authentication/callback`;
  * Permissions: `files.metadata.write`, `files.metadata.read`, `files.content.write`, `files.content.read`.
* (Optional) CUDA-capable GPU (see section [Setting up PyTorch+CUDA](#setting-up-pytorchcuda)) or use CPU-only (slower classification)
* (Optional) Docker Desktop with WSL 22.04 distribution (for containerized deployment)
---

## Setup
1. Clone this repository.
2. Run setup script in project directory:
  ```bash
  <your preferred base python> setup_env.py --app-key <your_dropbox_app_key> --app-secret <your_dropbox_app_secret>
  ```
This will:
* create a virtual environment;
* install dependencies;
* automatically detect and install the appropriate PyTorch+CUDA version (if a CUDA-capable GPU is detected, otherwise CPU-only version is installed).
* create a `.env` file with the provided Dropbox app key and secret as well as PyTorch+CUDA version and classification model name;

Alternatively, you can manually add an existing .env in the [docusight](./docusight/) directory with the following variables:
```sh
DROPBOX_APP_KEY=<your_dropbox_app_key>
DROPBOX_APP_SECRET=<your_dropbox_app_secret>
PYTORCH_CUDA_VERSION=<your_pytorch_cuda_version>  # e.g. cu126, cu117, cpu
CLASSIFICATION_MODEL_NAME=<your_classification_model_name>  # e.g. DTAI-KULeuven/robbert-v2-dutch-sentiment
DATABASE_URL=sqlite+aiosqlite:///./docusight.db
SESSION_SECRET_KEY=<your_random_secret_key>  # e.g. a random 32 alphanumeric string
```
Followed by running the setup script without arguments to install dependencies:
```bash
<your preferred base python> setup_env.py
```

---

## Setting up PyTorch+CUDA
To enable parallel processing of documents during classification, a PyTorch requires a [CUDA-capable GPU]((https://developer.nvidia.com/cuda-gpus)) on the host machine.
1. Install the appropriate NVIDIA drivers for your GPU from [NVIDIA's official website](https://www.nvidia.com/Download/index.aspx).
2. Use your driver version to find the compatible CUDA toolkit version [here](https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html). Note: check your current driver version with `nvidia-smi` command.
3. Check which PyTorch+CUDA version is compatible with your CUDA toolkit version [here](https://pytorch.org/get-started/locally/).
4. Set the `TORCH_CUDA_VERSION` variable in your environment (e.g. in `.env` file) to the appropriate version string (e.g. cu126).
5. Run the setup script from [Setup](#setup) again to install the correct PyTorch+CUDA version.
---

## Docker Setup
1. Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed with WSL 22.04 distribution.
2. Check the [Dockerfile](./Dockerfile) for any specific configurations.
3. (Optional) Modify the `PYTORCH_CUDA_VERSION` and `MODEL_NAME` environment variables in the Dockerfile if needed.
2. Build the Docker image:
   ```bash
   docker build -t docusight-app .
   ```
3. Run the Docker container (with GPU support):
   ```bash
   docker run --gpus all -p 8000:8000 --env-file ./docusight/.env docusight-app
   ```
---

## Project Structure

```
docusight/
│── main.py                 # FastAPI entrypoint
│── models.py               # SQLAlchemy models (User, Folder, Document, Classification)
│── database.py             # Database connection and session management
│── config.py               # Configuration settings
│── file_utils.py           # Folder scanning, metadata extraction, dropbox up- & download
│── classifier_pipeline.py  # Setup for huggingface model pipeline
│── dropbox.py              # Dropbox authentication, user specific client retrieval and cleanup
│── logging.py              # Logging configuration (same as FastAPI default)
│── routers/
│   |── authentication.py   # dropbox authentication endpoints
│   │── insight.py          # Folder insight endpoints
│   │── classification.py   # Document classification endpoints
tests/
│── conftest.py             # Test fixtures
│── test_authentication.py  # Tests for authentication endpoints
│── test_insight.py         # Tests for folder insight endpoints
│── test_classification.py  # Tests for classification endpoints
data/
│── sample_data             # Sample data provided in the case study assignment
│── sample_data.zip         # Zipped version of sample data (To be used in Insight endpoint)
```
---

## Useful Commands
Commands assume you are in the project root directory.
1. **Run the server (development mode)**

   ```bash
   fastapi dev ./docusight/main.py
   ```

2. **Run the server (production mode)**

   ```bash
   fastapi run ./docusight/main.py --host <host_ip> --port 8000
   ```
---

## Endpoints
*  Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in a browser for interactive Swagger UI.
* `POST /auth/dropbox` → Authenticates user via Dropbox OAuth2.
* `GET /insight/folder` → Returns total number of documents + metadata.
* `POST /classification/folder` → Runs classification/sentiment analysis on all documents.
---

## Scalability Considerations

* _Currently_, the service:
  * Is designed with FastAPI for asynchronous request handling, supporting multiple concurrent users.
  * Parallel classification of large volumes of documents is possible thanks to batched inference with Hugging Face Transformers (if using GPU).
  * Can be containerized with Docker for easy and secure deployment and scaling

* _In the future_, the service:
  * Can be extended with multiprocessing or task queues (Celery, Redis) for parallel document processing (in the insight endpoint).
  * Can be adapted to use more robust, cloud-based databases (PostgreSQL, MySQL) for better performance and scalability.
  * If the host machine's GPU has CUDA capability 7.0 or higher, the hugging face model can be precompiled with PyTorch 2.0+, for faster document classification.
  * Can use Docker Compose or Kubernetes for orchestrating multiple instances of the service and load balancing.
  * Can use a more specifically trained model for document classification, fine-tuned on the specific types of documents being processed. The current models do not perform consistently on the provided sample documents.
---