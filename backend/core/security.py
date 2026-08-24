"""
Sécurité : hash de mot de passe, JWT, dépendance FastAPI `get_current_user`.

C'est volontairement un module minimal — l'objectif est de couvrir
register/login/me pour le frontend. Les routes protégées supplémentaires
utilisent `Depends(get_current_user)` quand on en aura besoin.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import get_db

logger = logging.getLogger(__name__)


# ── Hash mot de passe (bcrypt direct, sans passlib) ───────────────────────
# Note: bcrypt limite les mots de passe à 72 octets. On tronque explicitement
# pour éviter les ValueError.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash un mot de passe en clair avec bcrypt."""
    password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe en clair contre sa version hashée."""
    try:
        plain_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as exc:  # hash malformé, encodage invalide, etc.
        logger.warning("verify_password a échoué: %s", exc)
        return False


# ── JWT ────────────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Encode un payload en JWT signé avec `JWT_SECRET_KEY`.
    `data` doit au moins contenir `{"sub": "<user_id>", "email": "<email>"}`.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── Dépendance FastAPI ────────────────────────────────────────────────────
async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Optional[AsyncSession] = Depends(get_db),
) -> dict:
    """
    Dépendance FastAPI : décode le JWT du header `Authorization: Bearer ...`
    et retourne la ligne utilisateur (dict) correspondante.

    Lève 401 si le token est absent/invalide/expiré, 503 si la DB est
    indisponible (mode OLLAMA_ONLY).
    """
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id_raw)
    except (JWTError, ValueError):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if db is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentification indisponible en mode Ollama-only.",
        )

    # Import local pour éviter les cycles (auth_service -> db -> ...).
    from services.auth_service import AuthService

    user = await AuthService(db).get_user_by_id(user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou désactivé.",
        )
    return user