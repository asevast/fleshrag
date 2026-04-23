#!/bin/bash
# Скрипт для проверки CUDA-поддержки в контейнерах

echo "=== Проверка CUDA поддержки ==="
echo ""

# Проверка NVIDIA Container Toolkit
echo "1. Проверка NVIDIA Container Toolkit:"
if command -v nvidia-smi &> /dev/null; then
    echo "   ✓ nvidia-smi доступен"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
else
    echo "   ✗ nvidia-smi не найден. Установите NVIDIA драйверы."
    exit 1
fi
echo ""

# Проверка docker runtime
echo "2. Проверка Docker NVIDIA runtime:"
docker info 2>/dev/null | grep -i "nvidia" || echo "   ⚠ NVIDIA runtime не найден в docker info"
echo ""

# Проверка CUDA в backend контейнере
echo "3. Проверка CUDA в backend контейнере:"
docker compose run --rm backend python -c "
import torch
print(f'   PyTorch version: {torch.__version__}')
print(f'   CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'   CUDA version: {torch.version.cuda}')
    print(f'   GPU device: {torch.cuda.get_device_name(0)}')
    print(f'   GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB')
else:
    print('   ⚠ CUDA не доступен. Проверьте NVIDIA Container Toolkit.')
"
echo ""

# Проверка CUDA в embed-service контейнере
echo "4. Проверка CUDA в embed-service контейнере:"
docker compose run --rm embed-service python -c "
import torch
from sentence_transformers import SentenceTransformer
print(f'   PyTorch version: {torch.__version__}')
print(f'   CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'   GPU device: {torch.cuda.get_device_name(0)}')
    model = SentenceTransformer('intfloat/multilingual-e5-large', device='cuda')
    print('   ✓ Модель успешно загружена на GPU')
else:
    print('   ⚠ CUDA не доступен.')
"
echo ""

echo "=== Проверка завершена ==="
