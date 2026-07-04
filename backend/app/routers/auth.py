"""Auth router — inscription, connexion, profil (US 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain import auth as auth_domain
from app.domain.models import (
    AuthResponse,
    ChessUsernameUpdate,
    UserCreate,
    UserLogin,
    UserProfile,
    UserSettingsUpdate,
)
from app.infrastructure import db_client
from app.routers.deps import get_current_user as _current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash bcrypt factice vérifié quand l'email est inconnu : le temps de réponse
# de /auth/login reste le même qu'avec un email existant, ce qui empêche
# d'énumérer les comptes en mesurant la latence.
_DUMMY_PW_HASH = auth_domain.hash_password("timing-equalizer")


def _to_profile(user: dict) -> UserProfile:
    return UserProfile(
        id=user["id"], email=user["email"], username=user["username"],
        chess_username=user.get("chess_username"),
        settings=user.get("settings") or {},
        xp=user.get("xp") or 0,
        level=user.get("level") or 1,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: UserCreate) -> AuthResponse:
    if db_client.find_user_by_email(body.email):
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    if db_client.find_user_by_username(body.username):
        raise HTTPException(status_code=400, detail="Pseudo déjà pris")
    pw_hash = auth_domain.hash_password(body.password)
    user = db_client.create_user(body.email, body.username, pw_hash)
    token = auth_domain.create_token(user["id"], user["email"])
    return AuthResponse(token=token, user=_to_profile(user))


@router.post("/login", response_model=AuthResponse)
def login(body: UserLogin) -> AuthResponse:
    user = db_client.find_user_by_email(body.email)
    hashed = user["password_hash"] if user else _DUMMY_PW_HASH
    if not auth_domain.verify_password(body.password, hashed) or not user:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    token = auth_domain.create_token(user["id"], user["email"])
    return AuthResponse(token=token, user=_to_profile(user))


@router.get("/me", response_model=UserProfile)
def me(user: dict = Depends(_current_user)) -> UserProfile:
    return _to_profile(user)


@router.patch("/me", response_model=UserProfile)
def update_me(body: ChessUsernameUpdate, user: dict = Depends(_current_user)) -> UserProfile:
    """US 6.3 — Lie/délie le pseudo Chess.com du profil de l'utilisateur authentifié uniquement."""
    updated = db_client.update_chess_username(user["id"], body.chess_username or None)
    return _to_profile(updated)


@router.patch("/me/settings", response_model=UserProfile)
def update_settings(body: UserSettingsUpdate, user: dict = Depends(_current_user)) -> UserProfile:
    """EPIC 18 (US 18.2/18.3) — Remplace les préférences de personnalisation (thème pièces/plateau)
    du profil de l'utilisateur authentifié uniquement.
    """
    updated = db_client.update_settings(user["id"], body.settings)
    return _to_profile(updated)
