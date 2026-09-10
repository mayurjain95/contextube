from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    chroma_persist_dir: str = "./chroma_store"
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    chat_model: str = "llama3.2"
    retrieval_score_threshold: float = 0.75

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
