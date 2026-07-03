"""Authentication domain logic — password hashing & JWT (US 7).

Uses stdlib HMAC-SHA256 for JWT and raw bcrypt for password hashing
so there are no broken native-library dependencies at test time.
In production, python-jose[cryptography] can replace the JWT part.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

import bcrypt as _bcrypt

from app.config import settings


# ---------------------------------------------------------------------------
# Custom exception (mirrors jose.JWTError for a compatible interface)
# ---------------------------------------------------------------------------

class JWTError(Exception):
    pass


# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT (HS256 via stdlib hmac + hashlib)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_token(user_id: str, email: str) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    exp = int(time.time()) + settings.jwt_expiry_days * 86400
    payload = _b64url_encode(json.dumps({"sub": user_id, "email": email, "exp": exp}).encode())
    signing_input = f"{header}.{payload}"
    secret = settings.jwt_secret.encode()
    sig = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise JWTError("Malformed token")
        header, payload_b64, sig_b64 = parts
        # Refuse tout algorithme autre que HS256 (attaque « alg confusion » /
        # "none") : la signature n'est jamais vérifiée avec un alg fourni par
        # l'attaquant, uniquement avec celui que le serveur émet.
        header_data = json.loads(_b64url_decode(header))
        if header_data.get("alg") != "HS256":
            raise JWTError("Unsupported algorithm")
        signing_input = f"{header}.{payload_b64}"
        secret = settings.jwt_secret.encode()
        expected_sig = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise JWTError("Invalid signature")
        payload: Dict[str, Any] = json.loads(_b64url_decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            raise JWTError("Token expired")
        return payload
    except JWTError:
        raise
    except Exception as exc:
        raise JWTError(str(exc)) from exc
