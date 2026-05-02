import time
from threading import Lock

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import jwt
from jose.exceptions import JWTError

from .config import Settings, get_settings


class AuthUser:
    def __init__(self, user_id: str, email: str | None, token: str):
        self.user_id = user_id
        self.email = email
        self.token = token


_jwks_cache: dict = {"keys": None, "fetched_at": 0.0}
_jwks_lock = Lock()
_JWKS_TTL = 600.0


def _jwks_url(supabase_url: str) -> str:
    return f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


def _get_jwks(supabase_url: str) -> list[dict]:
    now = time.time()
    if _jwks_cache["keys"] and now - _jwks_cache["fetched_at"] < _JWKS_TTL:
        return _jwks_cache["keys"]
    with _jwks_lock:
        if _jwks_cache["keys"] and time.time() - _jwks_cache["fetched_at"] < _JWKS_TTL:
            return _jwks_cache["keys"]
        r = httpx.get(_jwks_url(supabase_url), timeout=5.0)
        r.raise_for_status()
        keys = r.json().get("keys", [])
        _jwks_cache["keys"] = keys
        _jwks_cache["fetched_at"] = time.time()
        return keys


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    return header.split(" ", 1)[1].strip()


def _decode(token: str, settings: Settings) -> dict:
    try:
        unverified = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token header: {e}") from e

    alg = unverified.get("alg", "")
    kid = unverified.get("kid")

    if alg == "HS256":
        if not settings.SUPABASE_JWT_SECRET:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "JWT secret not configured")
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )

    if not settings.SUPABASE_URL:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "SUPABASE_URL not configured")

    keys = _get_jwks(settings.SUPABASE_URL)
    jwk = next((k for k in keys if k.get("kid") == kid), None)
    if jwk is None:
        _jwks_cache["fetched_at"] = 0.0
        keys = _get_jwks(settings.SUPABASE_URL)
        jwk = next((k for k in keys if k.get("kid") == kid), None)
    if jwk is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown signing key")

    return jwt.decode(
        token,
        jwk,
        algorithms=[alg],
        audience="authenticated",
    )


def require_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    token = _extract_bearer(request)
    try:
        payload = _decode(token, settings)
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}") from e

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing sub")
    return AuthUser(user_id=user_id, email=payload.get("email"), token=token)
