from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/habitcoach"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 24 * 7
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "qwen/qwen-2.5-72b-instruct"
    embedding_model: str = "openai/text-embedding-3-small"
    cors_origins: str = "http://localhost:3000"
    knowledge_dir: str = "data/knowledge"
    collection_name: str = "habit_knowledge"
    # Tabel `jurnal` di database lain (opsional). Kosong = pakai file .md bawaan saja.
    jurnal_database_url: str = ""
    use_builtin_knowledge: bool = True
    # Pengingat belajar (Web Push). Buat kunci dengan: python -m app.vapid
    timezone: str = "Asia/Jakarta"
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@example.com"


settings = Settings()
