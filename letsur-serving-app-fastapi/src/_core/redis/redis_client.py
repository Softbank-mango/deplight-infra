import redis as redis
import redis.asyncio as async_redis

from src._core.settings import app_settings, redis_settings

redis_connection_kwargs = {
    "socket_timeout": 3.0,
    "socket_connect_timeout": 10.0,
    # "max_connections":200
}

apool = async_redis.ConnectionPool.from_url(
    redis_settings.LETSUR_REDIS_URL, **redis_connection_kwargs
)
pool = redis.ConnectionPool.from_url(
    redis_settings.LETSUR_REDIS_URL, **redis_connection_kwargs
)

# redis_aclient = async_redis.Redis(connection_pool=apool)
# redis_client = redis.Redis(connection_pool=pool)


def get_client():
    return redis.Redis(connection_pool=pool)


def get_aclient():
    return async_redis.Redis(connection_pool=apool)
