"""
Service d'authentification : CRUD léger sur la table `users`.

Toutes les requêtes utilisent du SQL brut via `text()` (cohérent avec
le reste du projet, qui n'utilise pas l'ORM SQLAlchemy).
"""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password, verify_password
from models.schemas import UserCreate

logger = logging.getLogger(__name__)


# Colonnes qu'on renvoie au frontend (jamais `hashed_password`).
_PUBLIC_COLUMNS = (
    "id, email, full_name, role, is_active, created_at, hashed_password"
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Retourne l'utilisateur (dict complet, hash inclus) ou None."""
        result = await self.db.execute(
            text(
                f"SELECT {_PUBLIC_COLUMNS} FROM users WHERE email = :email LIMIT 1"
            ),
            {"email": email.lower()},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Retourne l'utilisateur (dict complet, hash inclus) ou None."""
        result = await self.db.execute(
            text(
                f"SELECT {_PUBLIC_COLUMNS} FROM users WHERE id = :id LIMIT 1"
            ),
            {"id": user_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def register_user(self, payload: UserCreate) -> dict:
        """
        Crée un nouvel utilisateur. Le mot de passe est hashé en bcrypt.

        Retourne la ligne créée (sans `hashed_password`).
        Lève une ValueError si l'email existe déjà (contrainte UNIQUE).
        """
        hashed = hash_password(payload.password)
        result = await self.db.execute(
            text(
                """
                INSERT INTO users (email, full_name, hashed_password, role, is_active)
                VALUES (:email, :full_name, :hashed_password, 'user', TRUE)
                RETURNING id, email, full_name, role, is_active, created_at
                """
            ),
            {
                "email": payload.email.lower(),
                "full_name": payload.full_name.strip(),
                "hashed_password": hashed,
            },
        )
        await self.db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("INSERT users n'a retourné aucune ligne.")
        return dict(row._mapping)

    async def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """
        Vérifie l'email + mot de passe.

        Retourne la ligne complète (hash inclus, pour debug) ou None si
        l'utilisateur n'existe pas OU si le mot de passe est incorrect.
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not user.get("is_active"):
            return None
        if not verify_password(password, user.get("hashed_password", "")):
            return None
        return user
