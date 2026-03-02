"""JWT validation for Keycloak tokens in Tornado.

Fetches the JWKS from Keycloak's well-known endpoint, caches the signing keys,
and validates Bearer tokens on protected endpoints.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import jwt
import structlog
from tornado.web import HTTPError

log = structlog.get_logger()

_jwks_cache: dict[str, Any] | None = None


def _fetch_jwks() -> dict[str, Any]:
    """Fetch and cache the JWKS from Keycloak."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    realm = os.getenv("KEYCLOAK_REALM", "demo")
    jwks_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            return _jwks_cache
    except Exception as exc:
        log.error("Failed to fetch JWKS from Keycloak", error=str(exc), url=jwks_url)
        raise HTTPError(503, reason="Authentication service unavailable") from exc


def invalidate_jwks_cache() -> None:
    """Clear the cached JWKS. Useful for key rotation."""
    global _jwks_cache
    _jwks_cache = None


def _decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT using Keycloak's public keys."""
    jwks_data = _fetch_jwks()
    jwks_client = jwt.PyJWKClient.__new__(jwt.PyJWKClient)
    jwks_client._jwk_set = jwt.api_jwk.PyJWKSet.from_dict(jwks_data)

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError:
        raise HTTPError(401, reason="Invalid token format") from None

    kid = unverified_header.get("kid")
    if kid is None:
        raise HTTPError(401, reason="Token missing key ID")

    try:
        signing_key = next(
            key for key in jwks_client._jwk_set.keys if key.key_id == kid
        )
    except StopIteration:
        invalidate_jwks_cache()
        jwks_data = _fetch_jwks()
        jwks_client._jwk_set = jwt.api_jwk.PyJWKSet.from_dict(jwks_data)
        try:
            signing_key = next(
                key for key in jwks_client._jwk_set.keys if key.key_id == kid
            )
        except StopIteration:
            raise HTTPError(401, reason="Token signed with unknown key") from None

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
    except jwt.ExpiredSignatureError:
        raise HTTPError(401, reason="Token expired") from None
    except jwt.InvalidTokenError:
        raise HTTPError(401, reason="Invalid token") from None

    return payload


def get_current_user(handler) -> dict[str, Any]:
    """Extract and validate the JWT from the Authorization header.

    Stores the decoded claims on the handler and returns them.
    Raises HTTPError 401 if no Bearer token is provided or if it is invalid.
    """
    auth_header = handler.request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPError(401, reason="Bearer token required")

    token = auth_header[len("Bearer "):]
    payload = _decode_token(token)
    handler._current_user = payload
    handler._raw_token = token
    return payload


def get_optional_user(handler) -> dict[str, Any] | None:
    """Like get_current_user but returns None when no token is present."""
    auth_header = handler.request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[len("Bearer "):]
    try:
        payload = _decode_token(token)
        handler._current_user = payload
        handler._raw_token = token
        return payload
    except Exception:
        return None
