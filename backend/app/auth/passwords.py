"""Mots de passe : seules des empreintes argon2 sont stockées, jamais le mot de passe lui-même."""

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128  # limite aussi le travail imposé au serveur par un mot de passe géant

_hasher = PasswordHasher()


class WeakPassword(ValueError):
    """Le mot de passe ne respecte pas les règles minimales."""


def validate_password_strength(password: str) -> None:
    """Règles minimales : 12 à 128 caractères, pas uniquement des espaces."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPassword(f"Le mot de passe ne doit pas dépasser {MAX_PASSWORD_LENGTH} caractères.")
    if not password.strip():
        raise WeakPassword("Le mot de passe ne peut pas être composé uniquement d'espaces.")


def hash_password(password: str) -> str:
    """Retourne l'empreinte argon2 d'un mot de passe valide (sel aléatoire inclus)."""
    validate_password_strength(password)
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Vrai si le mot de passe correspond à l'empreinte ; faux pour toute autre raison (aucune exception)."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Vrai si l'empreinte utilise d'anciens paramètres et doit être recalculée à la prochaine connexion."""
    return _hasher.check_needs_rehash(password_hash)


@lru_cache
def dummy_hash() -> str:
    """Empreinte factice : vérifiée quand le compte n'existe pas, pour que le temps de réponse ne révèle rien."""
    return _hasher.hash("empreinte-factice-pour-egaliser-le-temps-de-reponse")
