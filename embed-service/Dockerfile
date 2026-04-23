FROM nvidia/cuda:12.1.0-base-ubuntu22.04

WORKDIR /app

# Установка системных зависимостей и Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Установка CUDA-версии PyTorch и sentence-transformers
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.5.0 --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir \
    sentence-transformers==3.3.0 \
    transformers==4.46.0 \
    fastapi==0.115.0 \
    uvicorn==0.32.0 \
    pydantic==2.9.0

COPY server.py .

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
