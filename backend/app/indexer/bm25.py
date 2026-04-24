"""
BM25 индексация для гибридного поиска (BM25 + dense embeddings).
Используется Qdrant sparse vectors API.
"""

import re
from collections import Counter, defaultdict
from typing import List, Dict, Tuple
import math

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import settings

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
BM25_COLLECTION_NAME = "multimodal_rag_bm25"

# BM25 параметры
BM25_K1 = 1.5
BM25_B = 0.75


def tokenize(text: str) -> List[str]:
    """Токенизация текста: нижний регистр, удаление спецсимволов."""
    text = text.lower()
    tokens = re.findall(r'\b[a-zа-яё0-9]+\b', text, re.UNICODE)
    return [t for t in tokens if len(t) > 2]


class BM25Index:
    """Простая реализация BM25 для индексации и поиска."""
    
    def __init__(self):
        self.doc_freq: Dict[str, int] = defaultdict(int)  # DF токена
        self.doc_lengths: Dict[str, int] = {}  # Длина документа (в токенах)
        self.avg_doc_length: float = 0.0
        self.num_docs: int = 0
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(dict)  # token -> {doc_id: tf}
    
    def index_document(self, doc_id: str, text: str):
        """Индексация документа."""
        tokens = tokenize(text)
        doc_len = len(tokens)
        
        self.doc_lengths[doc_id] = doc_len
        self.num_docs += 1
        
        # Обновляем среднюю длину
        total_len = sum(self.doc_lengths.values())
        self.avg_doc_length = total_len / self.num_docs
        
        # TF документа
        tf = Counter(tokens)
        
        # Обновляем инвертированный индекс и DF
        for token, count in tf.items():
            self.inverted_index[token][doc_id] = count
            if doc_id not in self.inverted_index[token] or self.inverted_index[token][doc_id] == 0:
                self.doc_freq[token] += 1
    
    def score_query(self, query: str, doc_id: str) -> float:
        """BM25 score для документа по запросу."""
        tokens = tokenize(query)
        if not tokens:
            return 0.0
        
        score = 0.0
        doc_len = self.doc_lengths.get(doc_id, 0)
        
        for token in tokens:
            if token not in self.inverted_index or doc_id not in self.inverted_index[token]:
                continue
            
            tf = self.inverted_index[token][doc_id]
            df = self.doc_freq[token]
            
            # IDF
            idf = math.log((self.num_docs - df + 0.5) / (df + 0.5) + 1.0)
            
            # TF нормализованный
            tf_norm = tf * (BM25_K1 + 1) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / self.avg_doc_length))
            
            score += idf * tf_norm
        
        return score
    
    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """Поиск топ-K документов по запросу."""
        scores: Dict[str, float] = defaultdict(float)
        
        tokens = tokenize(query)
        for token in tokens:
            if token not in self.inverted_index:
                continue
            for doc_id, tf in self.inverted_index[token].items():
                # Приближённый score
                df = self.doc_freq[token]
                idf = math.log((self.num_docs - df + 0.5) / (df + 0.5) + 1.0)
                scores[doc_id] += idf * tf
        
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs[:top_k]


# Глобальный индекс (в памяти, пересоздаётся при старте)
_bm25_index: BM25Index | None = None


def get_bm25_index() -> BM25Index:
    global _bm25_index
    if _bm25_index is None:
        _bm25_index = BM25Index()
    return _bm25_index


def init_bm25_collection():
    """Создать коллекцию для sparse vectors (опционально, если нужно хранить в Qdrant)."""
    if not qdrant.collection_exists(BM25_COLLECTION_NAME):
        # Sparse vector config
        qdrant.create_collection(
            collection_name=BM25_COLLECTION_NAME,
            vectors_config={},  # Пусто, используем sparse
            sparse_vectors_config={
                "text": qdrant_models.SparseVectorParams()
            },
        )


def index_text_bm25(doc_id: str, text: str):
    """Индексация текста в BM25 индекс."""
    index = get_bm25_index()
    index.index_document(doc_id, text)


def search_bm25(query: str, top_k: int = 20) -> List[Tuple[str, float]]:
    """Поиск по BM25 индексу."""
    index = get_bm25_index()
    return index.search(query, top_k)
