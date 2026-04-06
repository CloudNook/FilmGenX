from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/filmgenx"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI 服务
    EVOLINK_API_KEY: str = ""
    EVOLINK_BASE_URL: str = "https://api.evolink.ai"
    HTTP_TRUST_ENV: bool = True
    EVOLINK_REQUEST_RETRIES: int = 3

    # Google
    GOOGLE_API_KEY: str = ""

    # 本地文件存储（开发环境备用）
    STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 100

    # 阿里云 OSS
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_ENDPOINT: str = ""
    OSS_BASE_DIR: str = "filmgenx"
    OSS_CDN_DOMAIN: str = ""


settings = Settings()
