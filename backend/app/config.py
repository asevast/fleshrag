from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_host: str = "http://ollama:11434"
    neuraldeep_base_url: str = "https://api.neuraldeep.ru/v1"
    neuraldeep_api_key: str | None = None
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    redis_url: str = "redis://redis:6379/0"
    default_provider: str = "cloud"
    local_llm_model: str = "qwen2.5:3b"
    local_embed_model: str = "multilingual-e5-large"
    local_rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    cloud_llm_model: str = "gpt-oss-120b"
    cloud_llm_economy_model: str = "qwen3.6-35b-a3b"
    cloud_embed_model: str = "e5-large"
    cloud_embed_alt_model: str = "bge-m3"
    cloud_rerank_model: str = "bge-reranker"
    database_url: str = "sqlite:////app/data/metadata.db"
    index_paths: str = "/mnt/indexed"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k_search: int = 20
    top_k_rerank: int = 5
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1000

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
