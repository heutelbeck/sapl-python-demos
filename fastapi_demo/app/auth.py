"""JWT validation dependency for Keycloak tokens.

Fetches the JWKS from Keycloak's well-known endpoint, caches the signing keys,
and validates Bearer tokens on protected endpoints.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import jwt
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = structlog.get_logger()

_bearer_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict[str, Any] | None = None


async def _fetch_jwks() -> dict[str, Any]:
    """Fetch and cache the JWKS from Keycloak."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    realm = os.getenv("KEYCLOAK_REALM", "demo")
    jwks_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            return _jwks_cache
    except Exception as exc:
        log.error("Failed to fetch JWKS from Keycloak", error=str(exc), url=jwks_url)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc


def invalidate_jwks_cache() -> None:
    """Clear the cached JWKS. Useful for key rotation."""
    global _jwks_cache
    _jwks_cache = None


async def _decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT using Keycloak's public keys."""
    jwks_data = await _fetch_jwks()
    jwks_client = jwt.PyJWKClient.__new__(jwt.PyJWKClient)
    jwks_client._jwk_set = jwt.api_jwk.PyJWKSet.from_dict(jwks_data)

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        ) from exc

    kid = unverified_header.get("kid")
    if kid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing key ID",
        )

    try:
        signing_key = next(
            key for key in jwks_client._jwk_set.keys if key.key_id == kid
        )
    except StopIteration as exc:
        # Key not found -- might be rotated. Clear cache and retry once.
        invalidate_jwks_cache()
        jwks_data = await _fetch_jwks()
        jwks_client._jwk_set = jwt.api_jwk.PyJWKSet.from_dict(jwks_data)
        try:
            signing_key = next(
                key for key in jwks_client._jwk_set.keys if key.key_id == kid
            )
        except StopIteration:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signed with unknown key",
            ) from exc

    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    realm = os.getenv("KEYCLOAK_REALM", "demo")
    issuer = f"{keycloak_url}/realms/{realm}"

    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    return payload


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency that extracts and validates the JWT.

    Stores the decoded claims on ``request.state.user`` and returns them.
    Raises 401 if no Bearer token is provided or if it is invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = await _decode_token(credentials.credentials)
    request.state.user = payload
    request.state.token = credentials.credentials
    return payload


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any] | None:
    """Like get_current_user but returns None when no token is present."""
    if credentials is None:
        return None

    try:
        payload = await _decode_token(credentials.credentials)
        request.state.user = payload
        request.state.token = credentials.credentials
        return payload
    except HTTPException:
        return None
