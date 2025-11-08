from functools import lru_cache

from src._core.utils import get_all_user_routers, is_quota_count_route


@lru_cache
def is_redis_need():
    for router in get_all_user_routers():
        for route in router.routes:
            if is_quota_count_route(route):
                return True

    return False
