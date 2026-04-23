FROM nvidia/cuda:12.1.0-base-ubuntu22.04

WORKDIR /app

# Установка системных зависимостей, включая ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3.12 \
    python3.12-venv \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .

# Установка CUDA-версии PyTorch и других зависимостей с GPU поддержкой
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.5.0 --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -e ".[dev]" --no-deps && \
    pip install --no-cache-dir \
    --no-deps \
    faster-whisper==1.1.0 \
    sentence-transformers==3.3.0 \
    transformers==4.46.0

COPY app/ ./app/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

