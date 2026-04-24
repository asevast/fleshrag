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

from app.config import settings
from app.indexer import bm25
from app.models.router import ModelRouter

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
router = ModelRouter()
COLLECTION_NAME = "multimodal_rag"
EMBED_BATCH_SIZE = 32


def generate_chunk_id(file_hash: str, chunk_index: int) -> str:
    """
    Генерирует стабильный chunk_id на основе file_hash и индекса чанка.
    
    Это обеспечивает идемпотентность: один и тот же файл всегда получит
    одинаковые chunk_id независимо от времени индексации.
    """
    content = f"{file_hash}_{chunk_index}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def _ensure_collection():
    if qdrant.collection_exists(COLLECTION_NAME):
        return

    vector_size = len(router.get_provider().embed_text("dimension probe"))
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE, on_disk=True),
        quantization_config=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            always_ram=False,
        ),
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
