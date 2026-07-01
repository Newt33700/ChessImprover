"""Dépendances FastAPI partagées — authentification (US 6.4).

Centralise la vérification du JWT pour éviter de dupliquer cette logique
dans chaque routeur qui a besoin de l'utilisateur authentifié.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain import auth as auth_domain
from app.infrastructure import db_client

_bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token manquant")
    try:
        payload = auth_domain.decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")
    user = db_client.find_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")
    return user


def get_current_user_id(user: dict = Depends(get_current_user)) -> str:
    """Raccourci pour les routes qui n'ont besoin que de l'ID (isolation par user_id)."""
    return user["id"]
