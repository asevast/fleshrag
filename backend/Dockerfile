FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей, включая ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

# Установка CUDA-версии PyTorch и других зависимостей с GPU поддержкой
# PyTorch с CUDA 12.1 для совместимости с драйвером NVIDIA
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.5.0 --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir \
    faster-whisper==1.1.0 \
    sentence-transformers==3.3.0 \
    transformers==4.46.0

COPY app/ ./app/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]