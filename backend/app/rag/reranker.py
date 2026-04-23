from sentence_transformers import CrossEncoder

from app.models import ModelRouter
from app.services.settings_service import SettingsService

_model = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _model


def rerank(query: str, documents: list, top_k: int = None) -> list:
    """Переранжирует документы с помощью cross-encoder.
    documents — список словарей с ключом 'snippet'.
    Возвращает отсортированный список топ-N результатов.
    """
    if not documents:
        return []

    runtime_settings = SettingsService()
    top_k = top_k or runtime_settings.get_top_k_rerank()

    provider = ModelRouter().get_provider()
    scores = provider.rerank(query, [doc.get("snippet", "") for doc in documents])

    if scores is None:
        pairs = [[query, doc.get("snippet", "")] for doc in documents]
        model = _get_model()
        scores = model.predict(pairs, show_progress_bar=False)

    for doc, score in zip(documents, scores):
        doc["rerank_score"] = float(score)

    sorted_docs = sorted(documents, key=lambda d: d["rerank_score"], reverse=True)
    return sorted_docs[:top_k]
