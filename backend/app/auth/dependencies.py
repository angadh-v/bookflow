from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, Dict

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

security = HTTPBearer(auto_error=False)
ALGORITHMS = ["RS256"]
JWKS_CACHE_SECONDS = 300


def _auth_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


@lru_cache(maxsize=2)
def _fetch_jwks(bucket: int) -> Dict[str, Any]:
    del bucket
    settings = get_settings()
    if not settings.auth0_domain:
        raise _auth_error("AUTH0_DOMAIN is not configured")

    jwks_url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    try:
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise _auth_error(f"Unable to fetch JWKS: {exc}") from exc

    return response.json()


def get_jwks() -> Dict[str, Any]:
    bucket = int(time.time() // JWKS_CACHE_SECONDS)
    return _fetch_jwks(bucket)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Dict[str, Any]:
    settings = get_settings()

    if settings.auth_disabled:
        return {"sub": "local-dev-user", "email": "local@example.com", "name": "Local User"}

    if not credentials:
        raise _auth_error("Missing authorization credentials")

    token = credentials.credentials

    try:
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)

        rsa_key: Dict[str, str] = {}
        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise _auth_error("Unable to find matching JWKS key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=ALGORITHMS,
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload
    except JWTError as exc:
        raise _auth_error(f"Invalid token: {exc}") from exc


def get_or_create_user(auth_payload: Dict[str, Any], db: Session) -> User:
    auth0_id = auth_payload.get("sub")
    email = auth_payload.get("email")
    name = auth_payload.get("name")

    if not auth0_id:
        raise _auth_error("Token payload missing 'sub'")

    user = db.query(User).filter(User.auth0_id == auth0_id).first()
    if user:
        if email and user.email != email:
            user.email = email
        if name is not None and user.name != name:
            user.name = name
        db.commit()
        db.refresh(user)
        return user

    if not email:
        email = f"{auth0_id}@unknown.local"

    user = User(auth0_id=auth0_id, email=email, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_db_user(
    auth_payload: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    return get_or_create_user(auth_payload, db)


def require_owner(
    auth_payload: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    settings = get_settings()

    # Keep local auth-disabled flows usable for development/tests.
    if settings.auth_disabled:
        return auth_payload

    owner_sub = settings.owner_auth0_sub.strip()
    if not owner_sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role is not configured",
        )

    if auth_payload.get("sub") != owner_sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner permissions required",
        )

    return auth_payload
