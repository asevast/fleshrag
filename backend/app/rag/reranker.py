# Placeholder for cross-encoder reranker
# from sentence_transformers import CrossEncoder
# model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query: str, documents: list, top_k: int = 5):
    # TODO: implement cross-encoder reranking
    return documents[:top_k]
