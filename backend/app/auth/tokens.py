"""Tokens d'accès : JWT signés (HS256), à durée limitée. La clé vient de JWT_SECRET_KEY (jamais du code)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"
ISSUER = "atlas"


class TokenError(Exception):
    """Token sans validité : invalide, expiré, falsifié ou mal formé (le détail n'est pas exposé)."""


def create_access_token(
    user_id: uuid.UUID, *, secret: str, expires_minutes: int, now: datetime | None = None
) -> tuple[str, datetime]:
    """Crée un token pour ``user_id`` ; retourne le token et sa date d'expiration (UTC)."""
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "iss": ISSUER,
        "iat": issued_at,
        "exp": expires_at,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM), expires_at


def decode_access_token(token: str, *, secret: str) -> uuid.UUID:
    """Vérifie signature, émetteur et expiration ; retourne l'identifiant de l'utilisateur.

    Seul l'algorithme HS256 est accepté (un token « alg: none » ou signé autrement est refusé).
    """
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
        return uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise TokenError("Token invalide ou expiré.") from None
