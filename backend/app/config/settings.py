from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "SSDD Agent Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SKIP_EXTERNAL_STARTUP: bool = False

    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "rsod_agent"
    DB_USER: str = "rsod_admin"
    DB_PASSWORD: str = "rsod_admin"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "rsod-agent-images"
    MINIO_SECURE: bool = False

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Embedding（RAG 向量检索用，默认复用 OPENAI_* 的 OpenAI 兼容 endpoint，
    # 如果 embedding 服务和对话 LLM 不是同一个供应商，可以在 .env 里单独覆盖）
    # 注意：EMBEDDING_MODEL 输出的向量维度必须和 app/entity/db_models.py 里的
    # EMBEDDING_DIM（当前 768）一致，改模型后要同步改 EMBEDDING_DIM 并重建
    # knowledge_chunks 表和索引。
    EMBEDDING_MODEL: str = "bge-base-zh-v1.5"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""

    @property
    def embedding_api_key(self) -> str:
        return self.EMBEDDING_API_KEY or self.OPENAI_API_KEY

    @property
    def embedding_base_url(self) -> str:
        return self.EMBEDDING_BASE_URL or self.OPENAI_BASE_URL

    # Training paths
    DATASET_BASE_DIR: str = "datasets/ssdd"
    TRAIN_OUTPUT_DIR: str = "runs/train"

    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    )

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"release", "prod", "production"}:
                return False
        return value

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

settings = Settings()
