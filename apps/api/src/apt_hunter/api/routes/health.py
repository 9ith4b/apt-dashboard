import asyncio
from collections.abc import Callable

from fastapi import APIRouter, Response, status
from minio import Minio
from pydantic import BaseModel
from redis import Redis
from sqlalchemy import text

from apt_hunter import __version__
from apt_hunter.config import get_settings
from apt_hunter.db.session import engine

router = APIRouter()


class LiveResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, bool]


def check_database() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_redis() -> bool:
    settings = get_settings()
    try:
        client: Redis = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        return bool(client.ping())
    except Exception:
        return False


def check_object_storage() -> bool:
    settings = get_settings()
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        client.list_buckets()
        return True
    except Exception:
        return False


async def run_check(check: Callable[[], bool]) -> bool:
    return await asyncio.to_thread(check)


@router.get("/live", response_model=LiveResponse)
def live() -> LiveResponse:
    return LiveResponse(status="ok", service="apt-hunter-api", version=__version__)


@router.get("/ready", response_model=ReadyResponse)
async def ready(response: Response) -> ReadyResponse:
    database, redis, object_storage = await asyncio.gather(
        run_check(check_database),
        run_check(check_redis),
        run_check(check_object_storage),
    )
    checks = {
        "database": database,
        "redis": redis,
        "object_storage": object_storage,
    }
    is_ready = all(checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(status="ready" if is_ready else "not_ready", checks=checks)
