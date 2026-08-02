
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from .config import settings


def _key_func(request: Request) -> str:
    """Rate-limit key. Trusts X-Forwarded-For only when TRUSTED_PROXY=true,
    otherwise falls back to the raw remote address (safe behind no proxy)."""
    if settings.trusted_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    headers_enabled=True,
    enabled=settings.rate_limit_enabled,
)
