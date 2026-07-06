"""Tests d'intégration — Lotus Mastery Engine (EPIC 38, US 38.1).

REMPLACE l'ex-EPIC 9 (répertoire de lignes + SRS SM-2, ``/openings/repertoire*``)
par l'arbre de positions (``/openings/trainer/*``). App de test minimale
(auth + openings_trainer routers), même motif que test_tactics_api.py.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure import db_client
from app.routers.auth import router as auth_router
from app.routers.openings_trainer import router as openings_router

_app = FastAPI()
_app.include_router(auth_router)
_app.include_router(openings_router)
client = TestClient(_app)

RUY_LOPEZ_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5"


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


def _signup_and_token(email="alice@ex.com", username="alice") -> str:
    r = client.post("/auth/signup", json={"email": email, "username": username, "password": "pass123"})
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _import(token: str, pgn: str = RUY_LOPEZ_PGN, name: str = "Ruy Lopez") -> dict:
    r = client.post(
        "/api/v1/openings/trainer/import",
        json={"repertoire_name": name, "pgn": pgn},
        headers=_auth(token),
    )
    return r.json()


class TestImportRepertoire:
    def test_valid_pgn_returns_repertoire_id_and_node_count(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/openings/trainer/import",
            json={"repertoire_name": "Ruy Lopez", "pgn": RUY_LOPEZ_PGN},
            headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["node_count"] == 5  # e4 e5 Nf3 Nc6 Bb5
        assert body["repertoire_id"]

    def test_invalid_pgn_returns_422(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/openings/trainer/import",
            json={"repertoire_name": "Bad", "pgn": "not a pgn"},
            headers=_auth(token),
        )
        assert r.status_code == 422

    def test_without_token_returns_401_or_403(self):
        r = client.post(
            "/api/v1/openings/trainer/import",
            json={"repertoire_name": "X", "pgn": RUY_LOPEZ_PGN},
        )
        assert r.status_code in (401, 403)


class TestNextMove:
    def test_first_move_of_a_freshly_imported_repertoire_is_immediately_trainable(self):
        token = _signup_and_token()
        _import(token)
        r = client.get("/api/v1/openings/trainer/next-move", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["session_complete"] is False
        assert body["status"] == "learning"
        assert body["mastery_score"] == 0
        assert body["rank"] == "Beginner"
        assert body["fen"] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def test_never_reveals_the_solution_move(self):
        token = _signup_and_token()
        _import(token)
        r = client.get("/api/v1/openings/trainer/next-move", headers=_auth(token))
        assert "move_san" not in r.json()

    def test_deeper_moves_are_locked_until_unlocked(self):
        token = _signup_and_token()
        _import(token)
        # Seul le 1er coup (e4) est débloqué : la session ne sert rien d'autre.
        r = client.get("/api/v1/openings/trainer/next-move", headers=_auth(token))
        assert r.json()["depth_level"] == 1

    def test_no_repertoire_at_all_returns_session_complete(self):
        token = _signup_and_token()
        r = client.get("/api/v1/openings/trainer/next-move", headers=_auth(token))
        assert r.json() == {
            "session_complete": True, "node_id": None, "fen": None, "depth_level": None,
            "is_mainline": None, "status": None, "mastery_score": None, "rank": None,
        }

    def test_without_token_returns_401_or_403(self):
        assert client.get("/api/v1/openings/trainer/next-move").status_code in (401, 403)


class TestSubmitAttempt:
    def _first_node_id(self, token: str) -> str:
        return client.get("/api/v1/openings/trainer/next-move", headers=_auth(token)).json()["node_id"]

    def test_correct_move_increases_mastery_score(self):
        token = _signup_and_token()
        _import(token)
        node_id = self._first_node_id(token)
        r = client.post(
            "/api/v1/openings/trainer/attempt",
            json={"node_id": node_id, "move_san": "e4"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["mastery_score"] == 15
        assert body["status"] == "review"
        assert body["srs_interval"] == 2

    def test_wrong_move_decreases_mastery_score_and_never_reveals_the_solution(self):
        token = _signup_and_token()
        _import(token)
        node_id = self._first_node_id(token)
        r = client.post(
            "/api/v1/openings/trainer/attempt",
            json={"node_id": node_id, "move_san": "d4"},
            headers=_auth(token),
        )
        body = r.json()
        assert body["mastery_score"] == 0  # borné à 0, pas -20
        assert "move_san" not in body

    def test_client_reported_success_flag_is_ignored_server_side_validates(self):
        # Même si un client malveillant envoie un move_san incorrect, il ne
        # peut pas se faire créditer un succès : seule la comparaison serveur
        # avec le nœud stocké compte (anti-triche, cf. Coach Tactique).
        token = _signup_and_token()
        _import(token)
        node_id = self._first_node_id(token)
        r = client.post(
            "/api/v1/openings/trainer/attempt",
            json={"node_id": node_id, "move_san": "totally-wrong"},
            headers=_auth(token),
        )
        assert r.json()["mastery_score"] == 0

    def test_reaching_intermediate_threshold_unlocks_direct_children(self):
        token = _signup_and_token()
        _import(token)
        node_id = self._first_node_id(token)
        # 3 succès : 15 -> 30 -> 45 (>= 40, seuil Intermediate)
        for _ in range(3):
            r = client.post(
                "/api/v1/openings/trainer/attempt",
                json={"node_id": node_id, "move_san": "e4"},
                headers=_auth(token),
            )
        assert r.json()["mastery_score"] == 45
        assert r.json()["unlocked_children"] == 1  # e5

        next_r = client.get("/api/v1/openings/trainer/next-move", headers=_auth(token))
        # e4 est maintenant en review (pas encore due) -> e5 (learning) est servi
        assert next_r.json()["depth_level"] == 2

    def test_unlocked_children_is_zero_below_threshold(self):
        token = _signup_and_token()
        _import(token)
        node_id = self._first_node_id(token)
        r = client.post(
            "/api/v1/openings/trainer/attempt",
            json={"node_id": node_id, "move_san": "e4"},
            headers=_auth(token),
        )
        assert r.json()["mastery_score"] == 15  # < 40
        assert r.json()["unlocked_children"] == 0

    def test_unknown_node_returns_404(self):
        token = _signup_and_token()
        r = client.post(
            "/api/v1/openings/trainer/attempt",
            json={"node_id": "missing", "move_san": "e4"},
            headers=_auth(token),
        )
        assert r.status_code == 404

    def test_locked_node_not_yet_unlocked_returns_404(self):
        token = _signup_and_token()
        r = _import(token)
        # On ne connaît l'ID d'un nœud verrouillé qu'en triche (jamais exposé
        # par l'API) — on le récupère ici directement via le store pour
        # vérifier que le serveur refuse bien une tentative dessus.
        from app.infrastructure import db_client as _db
        locked_node = next(
            n for n in _db._repertoire_nodes.values()
            if n["repertoire_id"] == r["repertoire_id"] and n["depth_level"] == 2
        )
        resp = client.post(
            "/api/v1/openings/trainer/attempt",
            json={"node_id": locked_node["id"], "move_san": "e5"},
            headers=_auth(token),
        )
        assert resp.status_code == 404

    def test_cannot_attempt_another_users_node(self):
        token_a = _signup_and_token(email="a@ex.com", username="usera")
        token_b = _signup_and_token(email="b@ex.com", username="userb")
        _import(token_a)
        node_id = self._first_node_id(token_a)
        r = client.post(
            "/api/v1/openings/trainer/attempt",
            json={"node_id": node_id, "move_san": "e4"},
            headers=_auth(token_b),
        )
        assert r.status_code == 404

    def test_without_token_returns_401_or_403(self):
        r = client.post(
            "/api/v1/openings/trainer/attempt", json={"node_id": "x", "move_san": "e4"},
        )
        assert r.status_code in (401, 403)
