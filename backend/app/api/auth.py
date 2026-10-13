"""Routes d'authentification : connexion (token) et profil.

Niveaux de permission : /auth/login = 0 (public, limité par essais) ; /auth/me = 1 (utilisateur connecté).
L'inscription n'existe pas dans l'API : les comptes se créent avec ``python -m app.manage create-user``.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_jwt_secret
from app.auth.service import AuthenticationFailed, TooManyAttempts, authenticate
from app.auth.tokens import create_access_token
from app.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["authentification"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Échange e-mail + mot de passe contre un token d'accès à durée limitée."""
    secret = require_jwt_secret(settings)
    correlation_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    try:
        user = authenticate(
            session,
            email=body.email,
            password=body.password,
            correlation_id=correlation_id,
            max_failures=settings.login_max_failures,
            window_minutes=settings.login_window_minutes,
        )
    except AuthenticationFailed:
        raise HTTPException(
            status_code=401, detail="Identifiants invalides.", headers={"WWW-Authenticate": "Bearer"}
        ) from None
    except TooManyAttempts:
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives. Réessaie plus tard.",
            headers={"Retry-After": str(settings.login_window_minutes * 60)},
        ) from None
    token, expires_at = create_access_token(
        user.id, secret=secret, expires_minutes=settings.session_duration_minutes
    )
    return TokenResponse(access_token=token, expires_at=expires_at)


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """Profil de l'utilisateur connecté (jamais d'empreinte de mot de passe)."""
    return UserResponse(id=user.id, email=user.email, display_name=user.display_name)
