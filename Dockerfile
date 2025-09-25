# Base image with CUDA and cuDNN (comment out if not using GPU)
FROM nvcr.io/nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04

# Set CUDA version for pytorch (should match the CUDA version in the base image and have the 'cu' prefix, no dots OR set to 'cpu' for CPU-only)
ENV PYTORCH_CUDA_VERSION=cu126

WORKDIR /docusight

# Silence interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive 

# Install Python 3.11 and pip
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3.11-distutils python3-pip && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

# Upgrade pip and install pip-tools
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install pip-tools

# Copy pyproject.toml and compile requirements.txt
COPY pyproject.toml ./
RUN pip-compile --generate-hashes --output-file=requirements.txt pyproject.toml

# Install Python dependencies
RUN python3 -m pip install -r requirements.txt

# Install local package in editable mode
RUN python3 -m pip install -e .

# Pre-install torch with cuda support
RUN python3 -m pip install torch --index-url https://download.pytorch.org/whl/${PYTORCH_CUDA_VERSION}

# Pre-download Hugging Face models (see README for other model options)
ENV MODEL_NAME=nlptown/bert-base-multilingual-uncased-sentiment
RUN python3 -c "from transformers import AutoModelForSequenceClassification; AutoModelForSequenceClassification.from_pretrained('${MODEL_NAME}')"

# Copy the rest of the application code
COPY . .

EXPOSE 8000

CMD ["python3", "-m", "fastapi", "run", "docusight/main.py", "--host", "0.0.0.0", "--port", "8000"]