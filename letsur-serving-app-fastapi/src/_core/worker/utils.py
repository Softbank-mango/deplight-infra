from functools import lru_cache
from src._core.utils import get_all_user_routers, is_async_route


@lru_cache
def is_celery_app_need():
    for router in get_all_user_routers():
        for route in router.routes:
            if is_async_route(route):
                return True

    return False
