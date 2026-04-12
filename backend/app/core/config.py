#backend/app/core/config.py

"""
Application configuration using Pydantic settings.
Loads from environment variables with sensible defaults.
"""

import os
from redis import Redis
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.constants import (
    DEFAULT_REDIS_HOST,
    DEFAULT_REDIS_PORT,
    DEFAULT_PII_TTL,
    DEFAULT_MODEL_NAME,
)


class Settings(BaseSettings):
    """Application settings loaded from environment and .env file."""

    # API Keys
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str

    # Database
    POSTGRES_URL: str
    QDRANT_HOST: str
    QDRANT_PORT: int

    REDIS_HOST: str = DEFAULT_REDIS_HOST
    REDIS_PORT: int = DEFAULT_REDIS_PORT
    PII_TTL: int = DEFAULT_PII_TTL  # 2 hours expiry

    # Model
    MODEL_NAME: str = DEFAULT_MODEL_NAME

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()


def get_redis_client() -> Redis:
    """Return a configured Redis client instance."""
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )