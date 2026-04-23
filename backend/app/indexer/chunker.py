from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

from app.config import settings


def chunk_text(text: str):
    splitter = SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    doc = Document(text=text)
    nodes = splitter.get_nodes_from_documents([doc])
    return [node.text for node in nodes]
