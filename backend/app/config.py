from __future__ import annotations

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    ollama_host: str = "http://ollama:11434"
    neuraldeep_base_url: str = "https://api.neuraldeep.ru/v1"
    neuraldeep_api_key: str = ""

    default_provider: str = "cloud"

    local_llm_model: str = "qwen2.5:3b"
    local_embed_model: str = "nomic-embed-text"
    local_rerank_model: str | None = None

    cloud_llm_model: str = "gpt-oss-120b"
    cloud_llm_economy_model: str = "qwen3.6-35b-a3b"
    cloud_embed_model: str = "e5-large"
    cloud_embed_alt_model: str = "bge-m3"
    cloud_rerank_model: str | None = "bge-reranker"

    embed_service_url: str = "http://embed-service:8001"

    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    redis_url: str = "redis://redis:6379/0"
    database_url: str = "sqlite:////app/data/metadata.db"

    index_paths: str = "/mnt/d"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k_search: int = 20
    top_k_rerank: int = 5

    llm_temperature: float = 0.3
    llm_max_tokens: int = 1000

    @computed_field
    @property
    def llm_model(self) -> str:
        if self.default_provider == "cloud" and self.neuraldeep_api_key:
            return self.cloud_llm_model
        return self.local_llm_model

    @computed_field
    @property
    def embed_model(self) -> str:
        if self.default_provider == "cloud" and self.neuraldeep_api_key:
            return self.cloud_embed_model
        return self.local_embed_model


settings = Settings()
