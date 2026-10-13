"""Dépendances FastAPI d'authentification : utilisateur courant déduit du token « Bearer »."""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.tokens import TokenError, decode_access_token
from app.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_session

_bearer = HTTPBearer(auto_error=False)
_UNAUTHORIZED = {"WWW-Authenticate": "Bearer"}


def require_jwt_secret(settings: Settings) -> str:
    """Retourne la clé de signature ou lève 503 si l'authentification n'est pas configurée."""
    if settings.jwt_secret_key is None:
        raise HTTPException(status_code=503, detail="Authentification non configurée (JWT_SECRET_KEY manquante).")
    return settings.jwt_secret_key.get_secret_value()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Utilisateur authentifié par le token ; 401 sinon (message identique quelle que soit la cause)."""
    secret = require_jwt_secret(settings)
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentification requise.", headers=_UNAUTHORIZED)
    try:
        user_id = decode_access_token(credentials.credentials, secret=secret)
    except TokenError:
        raise HTTPException(status_code=401, detail="Authentification requise.", headers=_UNAUTHORIZED) from None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Authentification requise.", headers=_UNAUTHORIZED)
    return user
