from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_host: str = "http://ollama:11434"
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    redis_url: str = "redis://redis:6379/0"
    llm_model: str = "qwen2.5:3b"
    embed_model: str = "nomic-embed-text"
    database_url: str = "sqlite:////app/data/metadata.db"
    index_paths: str = "/mnt/indexed"
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k_search: int = 20
    top_k_rerank: int = 5

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
