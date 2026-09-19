# Minimal image for running the FastAPI backend + static frontend.
# 3.12-slim is used deliberately over a newer Python: it's a well-established
# base with broad availability, safely inside this project's 3.10+ support
# range (see README) -- not chasing the newest interpreter for its own sake.
FROM python:3.12-slim

WORKDIR /app

# Install the CPU-only PyTorch build first, from PyTorch's own CPU wheel
# index. This app never uses a GPU, but PyPI's default "torch" wheel on
# Linux bundles several hundred MB of NVIDIA CUDA packages regardless --
# installing the CPU build here first means sentence-transformers (pulled
# in by requirements.txt below) finds torch already satisfied and never
# reaches for the CUDA-bundled variant.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
