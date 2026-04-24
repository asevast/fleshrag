from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    ScalarQuantizationConfig,
    ScalarType,
    VectorParams,
)

from app.config import settings
from app.indexer import bm25
from app.models.router import ModelRouter

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
router = ModelRouter()
COLLECTION_NAME = "multimodal_rag"
EMBED_BATCH_SIZE = 32


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


def embed_and_upsert(chunks: list, file_path: str, filename: str, file_type: str):
    _ensure_collection()
    provider = router.get_provider()

    points = []
    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start:batch_start + EMBED_BATCH_SIZE]
        embeddings = provider.embed_texts(batch)
        for index, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            global_index = batch_start + index
            doc_id = f"{file_path}_{global_index}"

            bm25.index_text_bm25(doc_id, chunk)

            points.append(
                PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "path": file_path,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_index": global_index,
                    },
                )
            )

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
