from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

from app.services.settings_service import SettingsService


def chunk_text(text: str):
    if not text or not text.strip():
        return []

    runtime_settings = SettingsService()
    splitter = SentenceSplitter(
        chunk_size=runtime_settings.get_chunk_size(),
        chunk_overlap=runtime_settings.get_chunk_overlap(),
    )
    doc = Document(text=text)
    nodes = splitter.get_nodes_from_documents([doc])
    return [node.text for node in nodes]
