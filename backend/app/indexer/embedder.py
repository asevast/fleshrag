import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from qdrant_client.http.models import ScalarQuantization, ScalarQuantizationConfig, ScalarType

from app.config import settings
from app.indexer import bm25
from app.models import ModelRouter

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
COLLECTION_NAME = "multimodal_rag"


def _ensure_collection(vector_size: int):
    if not qdrant.collection_exists(COLLECTION_NAME):
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE, on_disk=True),
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    always_ram=True,
                ),
            ),
        )
        return

    collection = qdrant.get_collection(COLLECTION_NAME)
    current_size = collection.config.params.vectors.size
    if current_size != vector_size:
        raise RuntimeError(
            f"Embedding dimension mismatch: collection={current_size}, requested={vector_size}. "
            "Switching embedding model requires reindexing into a matching collection."
        )


EMBED_BATCH_SIZE = 32


def delete_file_chunks(file_path: str):
    """Удаляет все точки Qdrant для указанного файла по payload-фильтру."""
    if not qdrant.collection_exists(COLLECTION_NAME):
        return
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
    
    qdrant.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[FieldCondition(key="path", match=MatchValue(value=file_path))]
        ),
        wait=True,
    )


def embed_and_upsert(chunks: list, file_path: str, filename: str, file_type: str):
    if not chunks:
        return
    provider = ModelRouter().get_provider()
    sample_vector = provider.embed_text(chunks[0])
    _ensure_collection(len(sample_vector))

    points = []
    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start:batch_start + EMBED_BATCH_SIZE]
        embeddings = provider.embed_texts(batch)
        for i, (chunk, emb) in enumerate(zip(batch, embeddings)):
            global_idx = batch_start + i
            # Генерируем UUID из пути и индекса для детерминированности
            doc_id_str = f"{file_path}_{global_idx}"
            doc_id = hashlib.md5(doc_id_str.encode()).hexdigest()
            
            # Индексируем в BM25
            bm25.index_text_bm25(doc_id_str, chunk)
            
            points.append(
                PointStruct(
                    id=doc_id,
                    vector=emb,
                    payload={
                        "text": chunk,
                        "path": file_path,
                        "filename": filename,
                        "file_type": file_type,
                        "chunk_index": global_idx,
                        "provider": provider.capabilities.provider,
                        "embed_model": provider.capabilities.embed_model,
                    },
                )
            )

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
