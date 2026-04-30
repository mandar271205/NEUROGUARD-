from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from supabase import create_client

from app.core.config import get_settings


bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    email: str | None = None
    claims: dict[str, Any] | None = None


def _jwks_url() -> str:
    settings = get_settings()
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_URL is not configured.",
        )
    return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


def _metadata_to_claims(user: Any) -> dict[str, Any]:
    metadata = getattr(user, "user_metadata", None) or {}
    app_metadata = getattr(user, "app_metadata", None) or {}
    return {
        "sub": getattr(user, "id", None),
        "email": getattr(user, "email", None),
        "user_metadata": metadata,
        "app_metadata": app_metadata,
    }


def _verify_with_supabase_auth(token: str) -> CurrentUser:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase service role key is not configured.")
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    result = client.auth.get_user(token)
    user = result.user
    claims = _metadata_to_claims(user)
    user_id = claims.get("sub")
    if not user_id:
        raise RuntimeError("Supabase Auth did not return a user id.")
    return CurrentUser(id=user_id, email=claims.get("email"), claims=claims)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    settings = get_settings()

    if credentials is None:
        if not settings.supabase_url:
            return CurrentUser(id="local-dev-user", email="local@neuroguard.dev", claims={})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    token = credentials.credentials
    jwks_error: Exception | None = None
    try:
        jwk_client = PyJWKClient(_jwks_url())
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        decode_kwargs: dict[str, Any] = {
            "algorithms": ["RS256"],
            "options": {"verify_aud": bool(settings.supabase_jwt_audience)},
        }
        if settings.supabase_jwt_audience:
            decode_kwargs["audience"] = settings.supabase_jwt_audience
        claims = jwt.decode(token, signing_key.key, **decode_kwargs)
    except Exception as exc:
        jwks_error = exc
        try:
            return _verify_with_supabase_auth(token)
        except Exception as auth_exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Supabase JWT.",
            ) from auth_exc

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a user id.",
        )
    return CurrentUser(id=user_id, email=claims.get("email"), claims=claims)
