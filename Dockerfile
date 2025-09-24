# FROM python:3.11-slim
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

WORKDIR /docusight

# # Install CUDA toolkit
# RUN apt-get update && \
#     apt-get install -y wget && \
#     wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb && \
#     apt-get install -y ./cuda-keyring_1.1-1_all.deb && \
#     apt-get update && \
#     apt-get install -y cuda-toolkit && \
#     rm -rf /var/lib/apt/lists/*
# RUN apt-get update && \
#     apt-get install -y python3 python3-pip
ENV DEBIAN_FRONTEND=noninteractive 
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-venv python3.11-distutils python3-pip && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

COPY . /docusight

ARG DROPBOX_APP_KEY
ARG DROPBOX_APP_SECRET

RUN python3 setup_env.py --app-key $DROPBOX_APP_KEY --app-secret $DROPBOX_APP_SECRET --use-global-python

EXPOSE 8000

CMD ["python3", "-m", "fastapi", "dev", "docusight/main.py", "--host", "0.0.0.0", "--port", "8000"]