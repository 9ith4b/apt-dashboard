from __future__ import annotations

import asyncio
import hmac
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from apt_hunter.config import Settings, get_settings
from apt_hunter.db.session import SessionLocal
from apt_hunter.services.auth import AuthPrincipal, load_principal, write_audit_log

ROLE_ORDER = {"viewer": 0, "analyst": 1, "admin": 2}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _expected_origin(request: Request) -> str:
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme).split(",")[0].strip()
    return f"{scheme}://{request.headers.get('host', request.url.netloc)}"


def _required_role(request: Request, api_prefix: str) -> str:
    relative = request.url.path.removeprefix(api_prefix).strip("/")
    if relative.startswith(("audit-logs", "auth/users", "ai")):
        return "admin"
    if request.method in SAFE_METHODS:
        return "viewer"
    if relative == "auth/logout" or relative.startswith("notifications"):
        return "viewer"
    if relative.startswith(("sources", "operations/jobs")):
        return "admin"
    return "analyst"


def _load(raw_token: str) -> AuthPrincipal | None:
    with SessionLocal() as session:
        return load_principal(session, raw_token)


def _audit(
    principal: AuthPrincipal | None,
    request: Request,
    response_status: int,
    *,
    result: str | None = None,
) -> None:
    relative = request.url.path.removeprefix(get_settings().api_prefix).strip("/")
    parts = relative.split("/") if relative else []
    object_type = parts[0] if parts else None
    object_id = parts[1] if len(parts) > 1 else None
    with SessionLocal() as session:
        write_audit_log(
            session,
            actor_user_id=principal.user_id if principal else None,
            action=f"{request.method} {relative}"[:100],
            object_type=object_type,
            object_id=object_id,
            result=result or ("succeeded" if response_status < 400 else "failed"),
            request_id=request.state.request_id,
            ip_address=_client_ip(request),
            details={"status_code": response_status},
        )


def _security_headers(response: Response, settings: Settings) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["Cache-Control"] = (
        "no-store"
        if response.headers.get("content-type", "").startswith("application/json")
        else response.headers.get("Cache-Control", "public, max-age=300")
    )
    if settings.session_secure_cookie:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        response: Response
        request.state.request_id = request.headers.get("x-request-id", str(uuid4()))[:64]
        request.state.principal = None
        path = request.url.path
        is_api = path.startswith(settings.api_prefix)
        is_health = path.startswith(f"{settings.api_prefix}/health/")
        is_login = path == f"{settings.api_prefix}/auth/login" and request.method == "POST"

        if is_login and settings.auth_enabled:
            origin = request.headers.get("origin")
            allowed_origins = {*settings.cors_origins, _expected_origin(request)}
            if origin not in allowed_origins:
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Origin validation failed"},
                )
                response.headers["X-Request-ID"] = request.state.request_id
                return _security_headers(response, settings)

        if not settings.auth_enabled or not is_api or is_health or is_login:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request.state.request_id
            return _security_headers(response, settings)

        raw_token = request.cookies.get(settings.session_cookie_name)
        principal = await asyncio.to_thread(_load, raw_token) if raw_token else None
        request.state.principal = principal
        if principal is None:
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
            )
            response.headers["X-Request-ID"] = request.state.request_id
            return _security_headers(response, settings)

        required = _required_role(request, settings.api_prefix)
        if ROLE_ORDER.get(principal.role, -1) < ROLE_ORDER[required]:
            await asyncio.to_thread(
                _audit, principal, request, status.HTTP_403_FORBIDDEN, result="forbidden"
            )
            response = JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"{required.title()} role required"},
            )
            response.headers["X-Request-ID"] = request.state.request_id
            return _security_headers(response, settings)

        if request.method not in SAFE_METHODS:
            origin = request.headers.get("origin")
            allowed_origins = {*settings.cors_origins, _expected_origin(request)}
            if origin not in allowed_origins:
                await asyncio.to_thread(
                    _audit, principal, request, status.HTTP_403_FORBIDDEN, result="origin_denied"
                )
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Origin validation failed"},
                )
                response.headers["X-Request-ID"] = request.state.request_id
                return _security_headers(response, settings)
            csrf_token = request.headers.get("x-csrf-token", "")
            if not hmac.compare_digest(csrf_token, principal.csrf_token):
                await asyncio.to_thread(
                    _audit, principal, request, status.HTTP_403_FORBIDDEN, result="csrf_denied"
                )
                response = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF validation failed"},
                )
                response.headers["X-Request-ID"] = request.state.request_id
                return _security_headers(response, settings)

        response = await call_next(request)
        if request.method not in SAFE_METHODS:
            await asyncio.to_thread(_audit, principal, request, response.status_code)
        response.headers["X-Request-ID"] = request.state.request_id
        return _security_headers(response, settings)
