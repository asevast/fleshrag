from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams, ScalarQuantizationConfig, ScalarType

from app.config import settings
from llama_index.embeddings.ollama import OllamaEmbedding

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
COLLECTION_NAME = "multimodal_rag"


def _ensure_collection():
    if not qdrant.collection_exists(COLLECTION_NAME):
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE, on_disk=True),
            quantization_config=ScalarQuantizationConfig(
                type=ScalarType.INT8,
                always_ram=False,
            ),
        )


EMBED_BATCH_SIZE = 32


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
    embedder = OllamaEmbedding(model_name=settings.embed_model, base_url=settings.ollama_host)

    points = []
    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start:batch_start + EMBED_BATCH_SIZE]
        embeddings = embedder.get_text_embedding_batch(batch)
        for i, (chunk, emb) in enumerate(zip(batch, embeddings)):
            global_idx = batch_start + i
            points.append(
                PointStruct(
                    id=f"{file_path}_{global_idx}",
                    vector=emb,
                    payload={
                        "text": chunk,
                        "path": file_path,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_index": global_idx,
                    },
                )
            )

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
