"""JWT validation for Keycloak tokens in Django async views.

Fetches the JWKS from Keycloak's well-known endpoint, caches the signing keys,
and validates Bearer tokens on protected endpoints.
"""
from __future__ import annotations

import os
from typing import Any

import httpx
import jwt
import structlog
from django.http import HttpRequest

log = structlog.get_logger()

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
        raise


def invalidate_jwks_cache() -> None:
    """Clear the cached JWKS. Useful for key rotation."""
    global _jwks_cache
    _jwks_cache = None


async def _decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT using Keycloak's public keys."""
    jwks_data = await _fetch_jwks()
    jwks_client = jwt.PyJWKClient.__new__(jwt.PyJWKClient)
    jwks_client._jwk_set = jwt.api_jwk.PyJWKSet.from_dict(jwks_data)

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if kid is None:
        raise ValueError("Token missing key ID")

    try:
        signing_key = next(
            key for key in jwks_client._jwk_set.keys if key.key_id == kid
        )
    except StopIteration:
        # Key not found -- might be rotated. Clear cache and retry once.
        invalidate_jwks_cache()
        jwks_data = await _fetch_jwks()
        jwks_client._jwk_set = jwt.api_jwk.PyJWKSet.from_dict(jwks_data)
        try:
            signing_key = next(
                key for key in jwks_client._jwk_set.keys if key.key_id == kid
            )
        except StopIteration as exc:
            raise ValueError("Token signed with unknown key") from exc

    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    realm = os.getenv("KEYCLOAK_REALM", "demo")
    issuer = f"{keycloak_url}/realms/{realm}"

    payload: dict[str, Any] = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=issuer,
        options={"verify_aud": False},
    )
    return payload


async def get_jwt_claims(request: HttpRequest) -> dict[str, Any] | None:
    """Extract and validate JWT claims from the Authorization header.

    Returns the decoded claims dict, or None if no valid token is present.
    Stores the claims on request.sapl_user and the raw token on
    request.sapl_token for downstream use.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    try:
        payload = await _decode_token(token)
        request.sapl_user = payload  # type: ignore[attr-defined]
        request.sapl_token = token  # type: ignore[attr-defined]
        return payload
    except (jwt.InvalidTokenError, ValueError) as exc:
        log.warning("JWT validation failed", error=str(exc))
        return None
