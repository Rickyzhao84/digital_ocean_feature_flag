# ...existing code...
from pydantic import BaseSettings, root_validator, validator
from urllib.parse import quote_plus
from typing import Optional


class Settings(BaseSettings):
    # Postgres connection components: supply via environment or .env
    DB_USERNAME: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_NAME: Optional[str] = None
    DB_SSLMODE: str = "require"

    # a constructed DATABASE_URL will be derived from the DB_* fields when not provided
    DATABASE_URL: Optional[str] = None

    # Other runtime config (can be provided via env)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    APP_HOST: Optional[str] = "0.0.0.0"
    APP_PORT: Optional[int] = 8000
    CACHE_TTL_SECONDS: Optional[int] = 30

    class Config:
        env_file = ".env"

    # JWT secret used for admin tokens (must be provided in prod)
    JWT_SECRET: Optional[str] = None

    @validator("DATABASE_URL", pre=True, always=True)
    def validate_database_url(cls, v, values):
        # Skip template strings from DigitalOcean
        if v and v.startswith("${"):
            return None
        return v

    @root_validator(pre=True)
    def build_database_url(cls, values):
        # If a full DATABASE_URL is not provided, attempt to build it from components
        if not values.get("DATABASE_URL"):
            user = values.get("DB_USERNAME")
            pwd = values.get("DB_PASSWORD")
            host = values.get("DB_HOST")
            port = values.get("DB_PORT")
            name = values.get("DB_NAME")
            ssl = values.get("DB_SSLMODE", "require")
            if user and pwd is not None and host and port and name:
                pwd_enc = quote_plus(str(pwd))
                values["DATABASE_URL"] = f"postgresql://{user}:{pwd_enc}@{host}:{port}/{name}?sslmode={ssl}"
        return values


def get_settings() -> Settings:
    return Settings()