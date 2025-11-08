from datetime import datetime, tzinfo
from typing import Optional

import pytz
from fastapi import Request, Response

from .dataclasses._internal import RequestCTX
from .exceptions.base import QuotaLimit
from .redis.redis_client import get_aclient, get_client
from .settings import app_settings
from .utils import get_request_context

QUOTA_KEY_FORMAT = app_settings.QUOTA_KEY_FORMAT
TZ_KOR = pytz.timezone("Asia/Seoul")


def _get_quota_key(ctx: RequestCTX, timezone: tzinfo = None):
    if timezone is None:
        timezone = TZ_KOR
    tz_date = datetime.fromtimestamp(ctx._request_time_ts, timezone)
    YYYYMM = f"{tz_date.year}{str(tz_date.month).zfill(2)}"
    return QUOTA_KEY_FORMAT.format(YYYYMM=YYYYMM)


def decr_quota(request: Request):
    ctx = get_request_context(request)
    ctx.is_quota_endpoint = True

    if not is_ok_decr_quota(request):
        # 차감할 필요가 없는 경우는 바로 나온다.
        return

    quota_key = _get_quota_key(ctx)
    c = get_client()
    v = c.decr(quota_key)

    ctx.decr_quota = True
    if v < 0:
        c.incr(quota_key)
        ctx.already_rollback = True
        raise QuotaLimit


async def adecr_quota(request: Request):
    ctx = get_request_context(request)
    ctx.is_quota_endpoint = True

    if not is_ok_decr_quota(request):
        # 차감할 필요가 없는 경우는 바로 나온다.
        return

    quota_key = _get_quota_key(ctx)
    c = get_aclient()
    v = await c.decr(quota_key)
    ctx.decr_quota = True
    if v < 0:
        await c.incr(quota_key)
        ctx.already_rollback = True
        raise QuotaLimit


def is_ok_decr_quota(request: Request):
    ctx = get_request_context(request)
    # 1. 이미 차감했으면 pass
    if ctx.decr_quota:
        return False
    # 2. Domain 및 White IP라서 예외면 pass
    if request.url.hostname == app_settings.LETSUR_ADMIN_URL_HOST:
        return False

    return True


def should_rollback_quota(request: Request, response: Optional[Response] = None):
    """
    response가 없는 경우 => handling되지 않은 exception이 나서 response를 얻어올 수 없는 케이스 => 쿼타를 낮춘 Request라면 다시 올려준다.
    """
    ctx = get_request_context(request)
    if (not ctx.decr_quota) or ctx.already_rollback:
        # 이 Request가 이전에 quota를 count했는지 확인.
        # Quota를 차감한 적 없거나, 이미 롤백했으면 롤백할 필요가 없다.
        return False
    if response and response.status_code <= 400:
        # 400번 오류만 사용자 과실로 취급하여 rollback 안함
        return False
    # 500번대 오류는 rb해준다.
    return True


def rb_quota(request: Request):
    ctx = get_request_context(request)
    quota_key = _get_quota_key(ctx)
    c = get_client()
    c.incr(quota_key)
    ctx.already_rollback = True


async def arb_quota(request: Request):
    ctx = get_request_context(request)
    quota_key = _get_quota_key(ctx)
    c = get_aclient()
    await c.incr(quota_key)
    ctx.already_rollback = True


#### 개발용 ####


def _flush_all():
    get_client().flushall()


def _set(i):
    kst_date = datetime.now(tz=TZ_KOR)
    YYYYMM = f"{kst_date.year}{str(kst_date.month).zfill(2)}"
    quota_key = QUOTA_KEY_FORMAT.format(YYYYMM=YYYYMM)
    get_client().set(quota_key, i)


def _set_quota_max():
    import sys

    MAX_NUM = sys.maxsize
    kst_date = datetime.now(tz=TZ_KOR)
    YYYYMM = f"{kst_date.year}{str(kst_date.month).zfill(2)}"
    quota_key = QUOTA_KEY_FORMAT.format(YYYYMM=YYYYMM)
    return get_client().set(quota_key, MAX_NUM)


def _get_val():
    kst_date = datetime.now(tz=TZ_KOR)
    YYYYMM = f"{kst_date.year}{str(kst_date.month).zfill(2)}"
    quota_key = QUOTA_KEY_FORMAT.format(YYYYMM=YYYYMM)
    return get_client().get(quota_key)


if __name__ == "__main__":
    # `python -m src._core.quota` 으로 로컬 개발환경 쿼타 세팅.
    print(_get_val())

    # set quota
    # _set(10)
