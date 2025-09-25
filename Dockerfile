FROM nvcr.io/nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04

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

COPY . /docusight

# Set build arguments for Dropbox credentials
ARG DROPBOX_APP_KEY
ARG DROPBOX_APP_SECRET

# Set CUDA version for pytorch (should match the CUDA version in the base image and have the 'cu' prefix, no dots)
ENV PYTORCH_CUDA_VERSION=cu126

# Run setup script with Dropbox credentials
RUN python3 setup_env.py --app-key $DROPBOX_APP_KEY --app-secret $DROPBOX_APP_SECRET --use-global-python

EXPOSE 8000

CMD ["python3", "-m", "fastapi", "run", "docusight/main.py", "--host", "0.0.0.0", "--port", "8000"]