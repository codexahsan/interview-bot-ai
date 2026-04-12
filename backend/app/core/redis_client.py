# backend/app/core/redis_client.py
from backend.app.core.config import get_redis_client

redis_client = get_redis_client()

def get_redis():
    return redis_client