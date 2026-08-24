"""
Routes d'authentification :
  - POST /auth/register   inscription (retourne JWT + profil)
  - POST /auth/login      connexion (retourne JWT + profil)
  - GET  /auth/me         profil de l'utilisateur courant (header Bearer)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, get_current_user
from db.database import get_db
from models.schemas import TokenResponse, UserCreate, UserLogin, UserResponse
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _build_token_response(user_row: dict) -> TokenResponse:
    """Construit un TokenResponse à partir d'une ligne DB (incluant id, email)."""
    user = UserResponse(
        id=user_row["id"],
        email=user_row["email"],
        full_name=user_row["full_name"],
        role=user_row["role"],
        is_active=user_row["is_active"],
        created_at=user_row["created_at"],
    )
    token = create_access_token(
        {"sub": str(user.id), "email": user.email},
    )
    return TokenResponse(access_token=token, user=user)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription d'un nouvel utilisateur",
)
async def register(
    payload: UserCreate,
    db: AsyncSession | None = Depends(get_db),
):
    """
    Crée un compte et retourne immédiatement un JWT pour démarrer une session.
    Mot de passe minimum : 6 caractères (vérifié côté Pydantic).
    """
    if db is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentification indisponible en mode Ollama-only.",
        )

    service = AuthService(db)
    existing = await service.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Un compte existe déjà avec cet email.",
        )

    try:
        created = await service.register_user(payload)
    except IntegrityError:
        # Course : quelqu'un a créé le même email entre le SELECT et l'INSERT.
        await db.rollback()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Un compte existe déjà avec cet email.",
        )

    logger.info("Nouvel utilisateur inscrit: id=%s email=%s", created["id"], created["email"])
    return _build_token_response(created)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Connexion (retourne un JWT)",
)
async def login(
    payload: UserLogin,
    db: AsyncSession | None = Depends(get_db),
):
    """
    Vérifie email + mot de passe, retourne un JWT + profil.
    Message d'erreur générique pour ne pas révéler si l'email existe.
    """
    if db is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentification indisponible en mode Ollama-only.",
        )

    user = await AuthService(db).authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    return _build_token_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Profil de l'utilisateur courant",
)
async def me(current_user: dict = Depends(get_current_user)):
    """
    Renvoie le profil de l'utilisateur identifié par le header
    `Authorization: Bearer <token>`.
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
    )
