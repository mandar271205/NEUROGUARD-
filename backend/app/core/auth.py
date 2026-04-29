from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Supabase JWT: {exc}",
        ) from exc

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a user id.",
        )
    return CurrentUser(id=user_id, email=claims.get("email"), claims=claims)
