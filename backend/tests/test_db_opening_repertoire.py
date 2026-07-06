"""Tests unitaires — store Lotus Mastery Engine (EPIC 38, US 38.1).

REMPLACE l'ex-store EPIC 9 (répertoire de lignes + SRS SM-2, ci-dessus dans
l'historique du dépôt) par l'arbre de nœuds + progression.
"""

from __future__ import annotations

import pytest

from app.infrastructure import db_client


@pytest.fixture(autouse=True)
def reset_db():
    db_client._reset_store()
    yield
    db_client._reset_store()


def _sample_nodes():
    """Un mini-arbre à 3 nœuds : 1. e4 e5 2. Nf3 — chacun enfant du précédent."""
    return [
        {"parent_index": None, "move_san": "e4", "move_fen": "fen-e4", "depth_level": 1, "is_mainline": True},
        {"parent_index": 0, "move_san": "e5", "move_fen": "fen-e5", "depth_level": 2, "is_mainline": True},
        {"parent_index": 1, "move_san": "Nf3", "move_fen": "fen-nf3", "depth_level": 3, "is_mainline": True},
    ]


class TestCreateRepertoireNodes:
    def test_assigns_a_real_id_to_each_node(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        assert len(created) == 3
        assert all(n["id"] for n in created)
        assert len({n["id"] for n in created}) == 3  # tous distincts

    def test_resolves_parent_index_to_the_previously_created_id(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        assert created[0]["parent_id"] is None
        assert created[1]["parent_id"] == created[0]["id"]
        assert created[2]["parent_id"] == created[1]["id"]

    def test_stamps_repertoire_id_and_user_id_on_every_node(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        assert all(n["repertoire_id"] == "repA" and n["user_id"] == "u1" for n in created)


class TestGetRepertoireNodeAndChildren:
    def test_get_repertoire_node_returns_known_node(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        node = db_client.get_repertoire_node(created[0]["id"])
        assert node["move_san"] == "e4"

    def test_get_repertoire_node_unknown_id_returns_none(self):
        assert db_client.get_repertoire_node("missing") is None

    def test_get_direct_children_returns_only_immediate_children(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        children = db_client.get_direct_children(created[0]["id"])
        assert [c["id"] for c in children] == [created[1]["id"]]

    def test_get_direct_children_of_a_leaf_is_empty(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        assert db_client.get_direct_children(created[2]["id"]) == []


class TestUnlockNodes:
    def test_unlocking_creates_a_learning_progress_row(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        unlocked = db_client.unlock_nodes("u1", [created[0]["id"]])
        assert unlocked == 1
        progress = db_client.get_node_progress("u1", created[0]["id"])
        assert progress["status"] == "learning"
        assert progress["mastery_score"] == 0
        assert progress["srs_interval"] == 1

    def test_unlocking_an_already_unlocked_node_is_idempotent(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[0]["id"]])
        second = db_client.unlock_nodes("u1", [created[0]["id"]])
        assert second == 0

    def test_unlocking_never_touches_a_node_locked_for_another_user(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[0]["id"]])
        assert db_client.get_node_progress("u2", created[0]["id"]) is None

    def test_get_node_progress_unknown_returns_none(self):
        assert db_client.get_node_progress("u1", "missing") is None


class TestUpdateNodeProgress:
    def test_persists_new_mastery_state(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[0]["id"]])
        updated = db_client.update_node_progress(
            "u1", created[0]["id"], 65, 8, "review", "2026-07-10T00:00:00+00:00",
        )
        assert updated["mastery_score"] == 65
        assert updated["srs_interval"] == 8
        assert updated["status"] == "review"
        assert db_client.get_node_progress("u1", created[0]["id"])["mastery_score"] == 65

    def test_creates_a_row_if_none_existed_yet(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        updated = db_client.update_node_progress(
            "u1", created[1]["id"], 15, 2, "review", "2026-07-10T00:00:00+00:00",
        )
        assert updated["mastery_score"] == 15


class TestGetNextTrainingNode:
    def test_learning_node_is_served_with_from_fen_of_its_parent(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[1]["id"]])  # e5, parent = e4
        entry = db_client.get_next_training_node("u1", "2026-07-10T00:00:00+00:00")
        assert entry["node_id"] == created[1]["id"]
        assert entry["from_fen"] == "fen-e4"
        assert entry["move_fen"] == "fen-e5"

    def test_root_node_from_fen_is_the_standard_starting_position(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[0]["id"]])  # e4, racine
        entry = db_client.get_next_training_node("u1", "2026-07-10T00:00:00+00:00")
        assert entry["from_fen"] == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def test_overdue_review_takes_priority_over_learning(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[0]["id"], created[1]["id"]])
        # created[0] reste "learning" ; created[1] passe en révision, déjà due.
        db_client.update_node_progress(
            "u1", created[1]["id"], 20, 2, "review", "2020-01-01T00:00:00+00:00",
        )
        entry = db_client.get_next_training_node("u1", "2026-07-10T00:00:00+00:00")
        assert entry["node_id"] == created[1]["id"]

    def test_review_not_yet_due_falls_back_to_learning(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[0]["id"], created[1]["id"]])
        db_client.update_node_progress(
            "u1", created[1]["id"], 20, 30, "review", "2099-01-01T00:00:00+00:00",
        )
        entry = db_client.get_next_training_node("u1", "2026-07-10T00:00:00+00:00")
        assert entry["node_id"] == created[0]["id"]

    def test_nothing_due_or_learning_returns_none(self):
        db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        assert db_client.get_next_training_node("u1", "2026-07-10T00:00:00+00:00") is None

    def test_never_returns_another_users_node(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[0]["id"]])
        assert db_client.get_next_training_node("u2", "2026-07-10T00:00:00+00:00") is None


class TestResetStore:
    def test_reset_store_clears_nodes_and_progress(self):
        created = db_client.create_repertoire_nodes("u1", "repA", _sample_nodes())
        db_client.unlock_nodes("u1", [created[0]["id"]])
        db_client._reset_store()
        assert db_client.get_repertoire_node(created[0]["id"]) is None
        assert db_client.get_node_progress("u1", created[0]["id"]) is None
