"""Auth router — inscription, connexion, profil (US 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain import auth as auth_domain
from app.domain.models import AuthResponse, UserCreate, UserLogin, UserProfile
from app.infrastructure import db_client

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


def _current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
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


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: UserCreate) -> AuthResponse:
    if db_client.find_user_by_email(body.email):
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    if db_client.find_user_by_username(body.username):
        raise HTTPException(status_code=400, detail="Pseudo déjà pris")
    pw_hash = auth_domain.hash_password(body.password)
    user = db_client.create_user(body.email, body.username, pw_hash)
    token = auth_domain.create_token(user["id"], user["email"])
    return AuthResponse(
        token=token,
        user=UserProfile(
            id=user["id"], email=user["email"], username=user["username"],
            chess_username=user.get("chess_username"),
        ),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: UserLogin) -> AuthResponse:
    user = db_client.find_user_by_email(body.email)
    if not user or not auth_domain.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    token = auth_domain.create_token(user["id"], user["email"])
    return AuthResponse(
        token=token,
        user=UserProfile(
            id=user["id"], email=user["email"], username=user["username"],
            chess_username=user.get("chess_username"),
        ),
    )


@router.get("/me", response_model=UserProfile)
def me(user: dict = Depends(_current_user)) -> UserProfile:
    return UserProfile(
        id=user["id"], email=user["email"], username=user["username"],
        chess_username=user.get("chess_username"),
    )
