from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    ScalarQuantizationConfig,
    ScalarType,
    VectorParams,
    FieldCondition,
    MatchValue,
    Filter,
    DeleteOperation,
)
import hashlib
from typing import Optional, Dict, Any

from app.config import settings
from app.indexer import bm25
from app.models.router import ModelRouter

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
router = ModelRouter()
COLLECTION_NAME = "multimodal_rag"
EMBED_BATCH_SIZE = 32

# Текущая версия схемы индекса
INDEX_VERSION = "1.0"


def generate_chunk_id(file_hash: str, chunk_index: int) -> str:
    """
    Генерирует стабильный chunk_id на основе file_hash и индекса чанка.
    
    Это обеспечивает идемпотентность: один и тот же файл всегда получит
    одинаковые chunk_id независимо от времени индексации.
    """
    content = f"{file_hash}_{chunk_index}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def _get_current_embed_model() -> str:
    """Возвращает текущую модель эмбеддингов."""
    provider = router.get_provider()
    return provider.capabilities.embed_model


def _get_vector_dimension() -> int:
    """Возвращает размерность векторов текущей модели."""
    provider = router.get_provider()
    embedding = provider.embed_text("dimension probe")
    return len(embedding)


def _ensure_collection():
    """
    Создаёт коллекцию если не существует и сохраняет metadata.
    
    Проверяет совместимость версии индекса и модели эмбеддингов.
    """
    if qdrant.collection_exists(COLLECTION_NAME):
        # Проверяем совместимость
        _check_index_compatibility()
        return

    # Получаем параметры текущей модели
    vector_size = _get_vector_dimension()
    embed_model = _get_current_embed_model()
    
    # Создаём коллекцию
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE, on_disk=True),
        quantization_config=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            always_ram=False,
        ),
    )
    
    # Сохраняем metadata
    _save_index_metadata(embed_model, vector_size)


def _save_index_metadata(embed_model: str, vector_dim: int):
    """Сохраняет metadata индекса в Qdrant collection config."""
    from qdrant_client.http import models as qdrant_models
    
    # Сохраняем в payload коллекции (через aliases или отдельный point)
    # Используем специальный point с ID "index_metadata" для хранения метаданных
    metadata_point = PointStruct(
        id="index_metadata",
        vector=[0.0] * vector_dim,  # Dummy vector
        payload={
            "type": "metadata",
            "embed_model": embed_model,
            "vector_dim": vector_dim,
            "index_version": INDEX_VERSION,
            "created_at": __import__('datetime').datetime.utcnow().isoformat(),
        }
    )
    
    qdrant.upsert(collection_name=COLLECTION_NAME, points=[metadata_point])


def _get_index_metadata() -> Optional[Dict[str, Any]]:
    """Получает metadata индекса из Qdrant."""
    try:
        points = qdrant.retrieve(
            collection_name=COLLECTION_NAME,
            ids=["index_metadata"],
        )
        if points and points[0].payload:
            return points[0].payload
    except Exception:
        pass
    return None


def _check_index_compatibility():
    """
    Проверяет совместимость текущего индекса с текущей моделью.
    
    Raises:
        RuntimeError: Если модель или размерность не совпадают
    """
    metadata = _get_index_metadata()
    if not metadata:
        # Metadata не найдено — предполагаем совместимость (старый индекс)
        return
    
    current_model = _get_current_embed_model()
    current_dim = _get_vector_dimension()
    
    indexed_model = metadata.get("embed_model")
    indexed_dim = metadata.get("vector_dim")
    indexed_version = metadata.get("index_version")
    
    # Проверяем совместимость
    if indexed_dim and indexed_dim != current_dim:
        raise RuntimeError(
            f"Index dimension mismatch: indexed with {indexed_dim}d vectors, "
            f"current model produces {current_dim}d vectors. "
            f"Reindex required. (indexed_model={indexed_model}, current_model={current_model})"
        )
    
    # Предупреждение о смене модели (но не блокируем если размерность совпадает)
    if indexed_model and indexed_model != current_model:
        import logging
        logging.warning(
            f"Embedding model changed: {indexed_model} → {current_model}. "
            f"Dimension match ({indexed_dim}d), but reindex recommended for optimal results."
        )


def delete_file_chunks(file_path: str):
    """Удаляет все точки Qdrant для указанного файла по payload-фильтру."""
    _ensure_collection()
    qdrant.delete(
        collection_name=COLLECTION_NAME,
        points_selector=None,
        wait=True,
        filter={
            "must": [
                {"key": "path", "match": {"value": file_path}}
            ]
        },
    )


def delete_outdated_chunks(file_path: str, current_chunk_ids: set):
    """
    Удаляет устаревшие чанки файла, которые не входят в текущий набор.
    
    Это более эффективная альтернатива полному удалению — сохраняем чанки,
    которые не изменились.
    """
    _ensure_collection()
    
    # Получаем все текущие chunk_id для этого файла
    existing_points = qdrant.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[FieldCondition(key="path", match=MatchValue(value=file_path))]
        ),
        limit=10000,  # Достаточно для большинства файлов
        with_payload=False,
        with_vectors=False,
    )[0]
    
    # Находим устаревшие chunk_id
    outdated_ids = []
    for point in existing_points:
        if point.id not in current_chunk_ids:
            outdated_ids.append(point.id)
    
    # Удаляем устаревшие
    if outdated_ids:
        qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=outdated_ids,
            wait=True,
        )


def embed_and_upsert(
    chunks: list,
    file_path: str,
    filename: str,
    file_type: str,
    file_hash: str,
):
    """
    Встраивает чанки и обновляет их в Qdrant с использованием стабильных chunk_id.
    
    Args:
        chunks: Список текстовых чанков
        file_path: Полный путь к файлу
        filename: Имя файла
        file_type: Тип файла (расширение)
        file_hash: MD5 хэш содержимого файла для генерации стабильных ID
    """
    _ensure_collection()
    provider = router.get_provider()

    current_chunk_ids = set()

    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start:batch_start + EMBED_BATCH_SIZE]
        embeddings = provider.embed_texts(batch)
        
        points = []
        for index, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            global_index = batch_start + index
            chunk_id = generate_chunk_id(file_hash, global_index)
            current_chunk_ids.add(chunk_id)
            
            # Индексируем в BM25 со стабильным ID
            bm25.index_text_bm25(chunk_id, chunk)
            
            points.append(
                PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "path": file_path,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_index": global_index,
                        "file_hash": file_hash,
                    },
                )
            )

        # Upsert: обновляет существующие или создаёт новые точки
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    
    # Удаляем устаревшие чанки (если файл уменьшился)
    delete_outdated_chunks(file_path, current_chunk_ids)
