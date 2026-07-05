"""Tests unitaires US 7 — Auth & Sync.

Couvre :
  - domain/auth.py  : hash, verify, create_token, decode_token
  - routers/auth.py : POST /auth/signup, POST /auth/login, GET /auth/me
  - routers/sync.py : POST /sync (Client Wins merge)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.domain.auth import (
    JWTError,
    _b64url_decode,
    _b64url_encode,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.infrastructure.db_client import _reset_store
from app.routers.auth import router as auth_router
from app.routers.sync import router as sync_router

# Minimal test app — avoids importing app.main (which requires python-chess)
_test_app = FastAPI()
_test_app.include_router(auth_router)
_test_app.include_router(sync_router)

client = TestClient(_test_app)


@pytest.fixture(autouse=True)
def reset_db():
    _reset_store()
    yield
    _reset_store()


# ── hash_password / verify_password ──────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        h = hash_password("secret123")
        assert h != "secret123"

    def test_hash_is_bcrypt(self):
        h = hash_password("secret123")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_verify_correct_password(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("mypassword")
        assert verify_password("wrong", h) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt

    def test_verify_password_returns_false_not_true_on_malformed_hash(self):
        # `except Exception: return False` — un hash corrompu/illisible par
        # bcrypt.checkpw ne doit JAMAIS être traité comme un mot de passe
        # valide (faille d'authentification si ça devenait `return True`).
        assert verify_password("anything", "not-a-valid-bcrypt-hash") is False


# ── _b64url_encode / _b64url_decode ────────────────────────────────────────────

class TestB64Url:
    @pytest.mark.parametrize("length", [0, 1, 2, 3, 4, 5, 6, 7, 8, 16, 17])
    def test_round_trip_all_padding_lengths(self, length):
        data = bytes(range(length))
        assert _b64url_decode(_b64url_encode(data)) == data

    def test_decode_without_padding_needed(self):
        # len(s) % 4 == 0 → padding calculé = 4 → aucun "=" ne doit être ajouté
        # (`if padding != 4` doit rester vrai seulement quand un padding réel
        # est nécessaire). 3 octets → base64 sans padding, longueur multiple de 4.
        data = b"123"
        encoded = _b64url_encode(data)
        assert len(encoded) % 4 == 0
        assert _b64url_decode(encoded) == data

    def test_strip_only_equals_not_other_trailing_chars(self):
        # `rstrip(b"=")` ne doit retirer QUE les "=" de padding, jamais un
        # caractère base64 valide (ex. "X") qui terminerait légitimement
        # l'encodage.
        data = b"\x00\x00\x17"  # encode en base64url vers "AAAX" (se termine par un X)
        encoded = base64.urlsafe_b64encode(data).decode()
        assert encoded == "AAAX"
        assert _b64url_encode(data) == encoded  # ne doit pas être tronqué en "AAA"


# ── create_token / decode_token ───────────────────────────────────────────────

class TestJWT:
    def test_create_and_decode_token(self):
        token = create_token("user-123", "test@example.com")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"

    def test_invalid_token_raises_jwterror(self):
        with pytest.raises(JWTError):
            decode_token("invalid.token.here")

    def test_tampered_token_raises_error(self):
        token = create_token("user-456", "a@b.com")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_token_contains_exp(self):
        token = create_token("user-789", "c@d.com")
        payload = decode_token(token)
        assert "exp" in payload

    def test_alg_none_token_rejected(self):
        """Un token forgé avec alg="none" (sans signature valide) est refusé."""
        import base64
        import json as _json

        def b64(d: dict) -> str:
            return base64.urlsafe_b64encode(_json.dumps(d).encode()).rstrip(b"=").decode()

        forged = f'{b64({"alg": "none", "typ": "JWT"})}.{b64({"sub": "admin", "exp": 9999999999})}.'
        with pytest.raises(JWTError):
            decode_token(forged)

    def test_tampered_alg_header_rejected(self):
        """Changer l'algorithme du header invalide le token (anti alg-confusion)."""
        import base64
        import json as _json

        token = create_token("user-1", "a@b.com")
        _, payload, sig = token.split(".")
        evil_header = base64.urlsafe_b64encode(
            _json.dumps({"alg": "HS512", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        with pytest.raises(JWTError):
            decode_token(f"{evil_header}.{payload}.{sig}")

    def test_header_has_exact_alg_and_typ_keys(self):
        import json as _json

        token = create_token("user-1", "a@b.com")
        header_b64 = token.split(".")[0]
        assert _json.loads(_b64url_decode(header_b64)) == {"alg": "HS256", "typ": "JWT"}

    def test_expiry_uses_86400_seconds_per_day(self):
        before = int(time.time())
        token = create_token("user-1", "a@b.com")
        payload = decode_token(token)
        expected = before + settings.jwt_expiry_days * 86400
        # Tolérance de 2s pour le temps d'exécution du test (pas plus : une
        # mutation `* 86401` décale l'expiration de `jwt_expiry_days` secondes,
        # largement au-delà de cette marge).
        assert expected <= payload["exp"] <= expected + 2

    def test_malformed_token_error_message(self):
        # Égalité exacte (pas `match=`, qui n'est qu'une recherche de
        # sous-chaîne et ne distinguerait pas "Malformed token" de
        # "XXMalformed tokenXX").
        with pytest.raises(JWTError) as exc_info:
            decode_token("only.two.parts.oops.four")
        assert str(exc_info.value) == "Malformed token"

    def test_unsupported_algorithm_error_message(self):
        import json as _json

        token = create_token("user-1", "a@b.com")
        _, payload, sig = token.split(".")
        evil_header = _b64url_encode(_json.dumps({"alg": "HS512", "typ": "JWT"}).encode())
        with pytest.raises(JWTError) as exc_info:
            decode_token(f"{evil_header}.{payload}.{sig}")
        assert str(exc_info.value) == "Unsupported algorithm"

    def test_invalid_signature_error_message(self):
        token = create_token("user-456", "a@b.com")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError) as exc_info:
            decode_token(tampered)
        assert str(exc_info.value) == "Invalid signature"

    def test_expired_token_error_message_and_boundary(self):
        import json as _json

        header = _b64url_encode(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        expired_payload = _b64url_encode(
            _json.dumps({"sub": "u", "email": "e", "exp": int(time.time()) - 10}).encode()
        )
        signing_input = f"{header}.{expired_payload}"
        sig = hmac.new(settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
        token = f"{signing_input}.{_b64url_encode(sig)}"
        with pytest.raises(JWTError) as exc_info:
            decode_token(token)
        assert str(exc_info.value) == "Token expired"

    def test_exp_exactly_now_is_not_expired(self):
        # `payload.get("exp", 0) < time.time()` : une expiration égale à
        # l'instant présent ne doit PAS être rejetée (limite stricte `<`,
        # pas `<=`).
        import json as _json

        exp = int(time.time()) + 5
        header = _b64url_encode(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload_b64 = _b64url_encode(_json.dumps({"sub": "u", "email": "e", "exp": exp}).encode())
        signing_input = f"{header}.{payload_b64}"
        sig = hmac.new(settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
        token = f"{signing_input}.{_b64url_encode(sig)}"
        payload = decode_token(token)
        assert payload["exp"] == exp

    def test_exp_equal_to_current_time_is_not_expired(self):
        # Frontière stricte : `exp < time.time()`, jamais `<=` — un jeton
        # dont l'expiration tombe exactement à l'instant présent doit
        # encore être accepté. `time.time()` figé pour un test déterministe.
        import json as _json
        from unittest.mock import patch

        frozen_now = 2_000_000_000.0
        header = _b64url_encode(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload_b64 = _b64url_encode(
            _json.dumps({"sub": "u", "email": "e", "exp": int(frozen_now)}).encode()
        )
        signing_input = f"{header}.{payload_b64}"
        sig = hmac.new(settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
        token = f"{signing_input}.{_b64url_encode(sig)}"
        with patch("app.domain.auth.time.time", return_value=frozen_now):
            payload = decode_token(token)
        assert payload["exp"] == int(frozen_now)


# ── POST /auth/signup ─────────────────────────────────────────────────────────

class TestSignup:
    def test_signup_returns_token_and_profile(self):
        r = client.post("/auth/signup", json={"email": "alice@ex.com", "username": "alice", "password": "pass123"})
        assert r.status_code == 201
        data = r.json()
        assert "token" in data
        assert data["user"]["email"] == "alice@ex.com"
        assert data["user"]["username"] == "alice"

    def test_signup_duplicate_email_returns_400(self):
        client.post("/auth/signup", json={"email": "bob@ex.com", "username": "bob", "password": "pass123"})
        r = client.post("/auth/signup", json={"email": "bob@ex.com", "username": "bob2", "password": "pass456"})
        assert r.status_code == 400

    def test_signup_duplicate_username_returns_400(self):
        client.post("/auth/signup", json={"email": "carol@ex.com", "username": "carol", "password": "pass123"})
        r = client.post("/auth/signup", json={"email": "carol2@ex.com", "username": "carol", "password": "pass456"})
        assert r.status_code == 400

    def test_signup_stores_user_in_db(self):
        client.post("/auth/signup", json={"email": "dave@ex.com", "username": "dave", "password": "pass123"})
        from app.infrastructure.db_client import find_user_by_email
        user = find_user_by_email("dave@ex.com")
        assert user is not None
        assert user["username"] == "dave"

    def test_signup_invalid_email_format_returns_422(self):
        r = client.post("/auth/signup", json={"email": "not-an-email", "username": "gina", "password": "pass123"})
        assert r.status_code == 422

    def test_signup_invalid_email_error_mentions_email(self):
        r = client.post("/auth/signup", json={"email": "not-an-email", "username": "gina", "password": "pass123"})
        detail = r.json()["detail"]
        assert any("email" in str(d.get("loc", "")) for d in detail)

    def test_signup_password_too_short_returns_422(self):
        r = client.post("/auth/signup", json={"email": "gina@ex.com", "username": "gina", "password": "abc"})
        assert r.status_code == 422

    def test_signup_response_includes_chess_username_field(self):
        r = client.post("/auth/signup", json={"email": "henri@ex.com", "username": "henri", "password": "pass123"})
        assert r.json()["user"]["chess_username"] is None

    def test_signup_stores_chess_username_none_in_db(self):
        client.post("/auth/signup", json={"email": "iris@ex.com", "username": "iris", "password": "pass123"})
        from app.infrastructure.db_client import find_user_by_email
        user = find_user_by_email("iris@ex.com")
        assert user["chess_username"] is None

    def test_signup_response_includes_default_xp_and_level(self):
        # EPIC 29 (US 29.1) : XP/niveau authoritatifs serveur, 0/1 par défaut.
        r = client.post("/auth/signup", json={"email": "jules@ex.com", "username": "jules", "password": "pass123"})
        assert r.json()["user"]["xp"] == 0
        assert r.json()["user"]["level"] == 1


# ── POST /auth/login ──────────────────────────────────────────────────────────

class TestLogin:
    def _create_user(self):
        client.post("/auth/signup", json={"email": "eve@ex.com", "username": "eve", "password": "pass123"})

    def test_login_with_correct_credentials(self):
        self._create_user()
        r = client.post("/auth/login", json={"email": "eve@ex.com", "password": "pass123"})
        assert r.status_code == 200
        assert "token" in r.json()

    def test_login_with_wrong_password_returns_401(self):
        self._create_user()
        r = client.post("/auth/login", json={"email": "eve@ex.com", "password": "wrongpassword"})
        assert r.status_code == 401

    def test_login_with_unknown_email_returns_401(self):
        r = client.post("/auth/login", json={"email": "nobody@ex.com", "password": "pass123"})
        assert r.status_code == 401

    def test_login_returns_user_profile(self):
        self._create_user()
        r = client.post("/auth/login", json={"email": "eve@ex.com", "password": "pass123"})
        data = r.json()
        assert data["user"]["email"] == "eve@ex.com"
        assert data["user"]["username"] == "eve"


# ── GET /auth/me ──────────────────────────────────────────────────────────────

class TestMe:
    def _signup_and_token(self) -> str:
        r = client.post("/auth/signup", json={"email": "frank@ex.com", "username": "frank", "password": "pass123"})
        return r.json()["token"]

    def test_me_with_valid_token(self):
        token = self._signup_and_token()
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "frank"

    def test_me_without_token_returns_403(self):
        r = client.get("/auth/me")
        assert r.status_code in (401, 403)

    def test_me_with_invalid_token_returns_401(self):
        r = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code == 401

    def test_me_includes_chess_username_field(self):
        token = self._signup_and_token()
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.json()["chess_username"] is None


# ── PATCH /auth/me (US 6.3) ─────────────────────────────────────────────────────

class TestUpdateMe:
    def _signup_and_token(self, email="ida@ex.com", username="ida") -> str:
        r = client.post("/auth/signup", json={"email": email, "username": username, "password": "pass123"})
        return r.json()["token"]

    def test_update_chess_username_success(self):
        token = self._signup_and_token()
        r = client.patch(
            "/auth/me", json={"chess_username": "MagnusCarlsen"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["chess_username"] == "MagnusCarlsen"

    def test_update_chess_username_persists(self):
        token = self._signup_and_token()
        client.patch(
            "/auth/me", json={"chess_username": "Hikaru"},
            headers={"Authorization": f"Bearer {token}"},
        )
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.json()["chess_username"] == "Hikaru"

    def test_update_chess_username_invalid_format_returns_422(self):
        token = self._signup_and_token()
        r = client.patch(
            "/auth/me", json={"chess_username": "a"},  # trop court (< 3)
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_update_chess_username_rejects_special_characters(self):
        token = self._signup_and_token()
        r = client.patch(
            "/auth/me", json={"chess_username": "bad user!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_update_chess_username_empty_clears_it(self):
        token = self._signup_and_token()
        client.patch(
            "/auth/me", json={"chess_username": "Hikaru"},
            headers={"Authorization": f"Bearer {token}"},
        )
        r = client.patch(
            "/auth/me", json={"chess_username": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["chess_username"] is None

    def test_update_chess_username_without_token_returns_401_or_403(self):
        r = client.patch("/auth/me", json={"chess_username": "Hikaru"})
        assert r.status_code in (401, 403)

    def test_update_chess_username_only_affects_own_profile(self):
        token_a = self._signup_and_token(email="jack@ex.com", username="jack")
        token_b = self._signup_and_token(email="kate@ex.com", username="kate")
        client.patch(
            "/auth/me", json={"chess_username": "JackOnChessCom"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        r_b = client.get("/auth/me", headers={"Authorization": f"Bearer {token_b}"})
        assert r_b.json()["chess_username"] is None


class TestUpdateSettings:
    """EPIC 18 (US 18.2/18.3) — PATCH /auth/me/settings."""

    def _signup_and_token(self, email="theo@ex.com", username="theo") -> str:
        r = client.post("/auth/signup", json={"email": email, "username": username, "password": "pass123"})
        return r.json()["token"]

    def test_settings_default_to_empty_object_on_signup(self):
        r = client.post("/auth/signup", json={"email": "new@ex.com", "username": "newu", "password": "pass123"})
        assert r.json()["user"]["settings"] == {}

    def test_update_settings_success(self):
        token = self._signup_and_token()
        settings = {"piece_theme": "cyber-tactics", "board_theme": "slate"}
        r = client.patch(
            "/auth/me/settings", json={"settings": settings},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["settings"] == settings

    def test_update_settings_persists(self):
        token = self._signup_and_token()
        client.patch(
            "/auth/me/settings", json={"settings": {"piece_theme": "cyber-tactics"}},
            headers={"Authorization": f"Bearer {token}"},
        )
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.json()["settings"] == {"piece_theme": "cyber-tactics"}

    def test_update_settings_replaces_rather_than_merges(self):
        token = self._signup_and_token()
        client.patch(
            "/auth/me/settings", json={"settings": {"piece_theme": "cyber-tactics", "board_theme": "slate"}},
            headers={"Authorization": f"Bearer {token}"},
        )
        r = client.patch(
            "/auth/me/settings", json={"settings": {"board_theme": "ocean"}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["settings"] == {"board_theme": "ocean"}

    def test_update_settings_accepts_arbitrary_keys(self):
        # Permissif par conception (US 18.2) : aucune clé n'est figée dans le contrat.
        token = self._signup_and_token()
        r = client.patch(
            "/auth/me/settings", json={"settings": {"sound_enabled": True, "board_size": 480}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["settings"] == {"sound_enabled": True, "board_size": 480}

    def test_update_settings_rejects_non_object_settings(self):
        token = self._signup_and_token()
        r = client.patch(
            "/auth/me/settings", json={"settings": "not-an-object"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_update_settings_without_token_returns_401_or_403(self):
        r = client.patch("/auth/me/settings", json={"settings": {"piece_theme": "cyber-tactics"}})
        assert r.status_code in (401, 403)

    def test_update_settings_only_affects_own_profile(self):
        token_a = self._signup_and_token(email="leo@ex.com", username="leo")
        token_b = self._signup_and_token(email="mia@ex.com", username="mia")
        client.patch(
            "/auth/me/settings", json={"settings": {"piece_theme": "cyber-tactics"}},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        r_b = client.get("/auth/me", headers={"Authorization": f"Bearer {token_b}"})
        assert r_b.json()["settings"] == {}


# ── POST /sync ─────────────────────────────────────────────────────────────────

class TestSync:
    def _signup_and_token(self) -> str:
        r = client.post("/auth/signup", json={"email": "grace@ex.com", "username": "grace", "password": "pass123"})
        return r.json()["token"]

    def test_sync_returns_merged_data(self):
        token = self._signup_and_token()
        payload = {
            "games": [{"game_id": "g1", "accuracy": 75.0, "date": "2026-01-01T00:00:00Z"}],
            "srs_cards": [{"id": "c1", "fen": "start", "ef": 2.5, "interval": 1, "reps": 0, "due": "2026-06-29"}],
        }
        r = client.post("/sync", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data["games"]) == 1
        assert data["games"][0]["game_id"] == "g1"
        assert len(data["srs_cards"]) == 1

    def test_sync_client_wins_on_conflict(self):
        token = self._signup_and_token()
        # First sync: low accuracy
        client.post("/sync", json={"games": [{"game_id": "g1", "accuracy": 50.0}], "srs_cards": []},
                    headers={"Authorization": f"Bearer {token}"})
        # Second sync: higher accuracy — client wins
        r = client.post("/sync", json={"games": [{"game_id": "g1", "accuracy": 90.0}], "srs_cards": []},
                        headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        assert data["games"][0]["accuracy"] == 90.0

    def test_sync_without_token_returns_401(self):
        r = client.post("/sync", json={"games": [], "srs_cards": []})
        assert r.status_code in (401, 403)

    def test_sync_accumulates_different_games(self):
        token = self._signup_and_token()
        client.post("/sync", json={"games": [{"game_id": "g1"}], "srs_cards": []},
                    headers={"Authorization": f"Bearer {token}"})
        r = client.post("/sync", json={"games": [{"game_id": "g2"}], "srs_cards": []},
                        headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        game_ids = [g["game_id"] for g in data["games"]]
        assert "g1" in game_ids
        assert "g2" in game_ids
