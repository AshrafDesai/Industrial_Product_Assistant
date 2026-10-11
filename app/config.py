
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/auto"

    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"

    chroma_dir: Path = ROOT_DIR / "data" / "chroma"
    upload_dir: Path = ROOT_DIR / "data" / "documents"
    top_k: int = 5

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
