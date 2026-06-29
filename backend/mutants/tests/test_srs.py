"""Tests unitaires du moteur SRS SM-2 — conçus pour tuer 100% des mutations mutmut.

Chaque branche (quality < 3, reps == 1/2/3+, EF clamp), chaque constante et
chaque formule de calcul d'intervalle est exercé par des assertions exactes.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.models import SRSCard
from app.domain.srs_engine import (
    EF_MIN,
    create_card,
    get_due_cards,
    review_card,
)


# ===================================================================
# create_card
# ===================================================================

class TestCreateCard:
    """Tests pour create_card(id, fen, solution) → SRSCard."""

    def test_creates_card_with_defaults(self):
        card = create_card("tactic_1", "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4", "Bxf7+")
        assert card.id == "tactic_1"
        assert card.ef == 2.5
        assert card.interval == 1
        assert card.reps == 0
        assert card.due == date.today().isoformat()

    def test_preserves_fen_and_solution(self):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        card = create_card("opening_1", fen, "e5")
        assert card.fen == fen
        assert card.solution == "e5"

    def test_ef_minimum_constant(self):
        """EF_MIN doit être 1.3."""
        assert EF_MIN == 1.3


# ===================================================================
# review_card — branches qualité < 3 (échec)
# ===================================================================

class TestReviewCardFailure:
    """Tests pour review_card quand quality < 3 (réinitialisation)."""

    def _base_card(self) -> SRSCard:
        return create_card("test_1", "fen", "e4")

    def test_quality_0_resets(self):
        card = self._base_card()
        result = review_card(card, 0)
        assert result.reps == 0
        assert result.interval == 1
        assert result.due == date.today().isoformat()

    def test_quality_1_resets(self):
        card = self._base_card()
        result = review_card(card, 1)
        assert result.reps == 0
        assert result.interval == 1

    def test_quality_2_resets(self):
        card = self._base_card()
        result = review_card(card, 2)
        assert result.reps == 0
        assert result.interval == 1

    def test_failure_preserves_ef(self):
        """En cas d'échec, l'EF n'est PAS modifié (contrairement au succès)."""
        card = self._base_card()
        card = SRSCard(**{**card.dict(), "ef": 2.8})
        result = review_card(card, 0)
        assert result.ef == 2.8

    def test_failure_preserves_id(self):
        card = self._base_card()
        result = review_card(card, 1)
        assert result.id == "test_1"

    def test_failure_preserves_fen_and_solution(self):
        card = self._base_card()
        result = review_card(card, 0)
        assert result.fen == "fen"
        assert result.solution == "e4"


# ===================================================================
# review_card — branches qualité >= 3 (succès)
# ===================================================================

class TestReviewCardSuccess:
    """Tests pour review_card quand quality >= 3 (mise à jour SM-2)."""

    def _base_card(self) -> SRSCard:
        return create_card("test_1", "fen", "e4")

    def test_quality_3_increases_reps(self):
        card = self._base_card()
        result = review_card(card, 3)
        assert result.reps == 1
        assert result.interval == 1

    def test_quality_4_increases_reps(self):
        card = self._base_card()
        result = review_card(card, 4)
        assert result.reps == 1

    def test_quality_5_increases_reps(self):
        card = self._base_card()
        result = review_card(card, 5)
        assert result.reps == 1

    def test_first_rep_interval_is_1(self):
        card = self._base_card()
        result = review_card(card, 3)
        assert result.interval == 1

    def test_second_rep_interval_is_6(self):
        card = self._base_card()
        card = review_card(card, 3)  # reps=1, interval=1
        result = review_card(card, 4)  # reps=2
        assert result.reps == 2
        assert result.interval == 6

    def test_third_rep_interval_is_interval_times_ef(self):
        card = self._base_card()
        card = review_card(card, 4)  # reps=1
        card = review_card(card, 4)  # reps=2, interval=6
        # Quality 4 : delta = 0.1 - 1*(0.08+1*0.02) = 0.1-0.1 = 0
        # ef reste 2.5, interval = round(6 * 2.5) = 15
        result = review_card(card, 4)
        assert result.reps == 3
        assert result.interval == 15

    def test_ef_calculation_quality_5(self):
        """Quality 5 : delta = 0.1 - 0*(...) = 0.1, new_ef = 2.5 + 0.1 = 2.6."""
        card = self._base_card()
        result = review_card(card, 5)
        assert result.ef == 2.6

    def test_ef_calculation_quality_4(self):
        """Quality 4 : delta = 0.1 - 1*(0.08+1*0.02) = 0.1-0.1 = 0."""
        card = self._base_card()
        result = review_card(card, 4)
        assert result.ef == 2.5

    def test_ef_calculation_quality_3(self):
        """Quality 3 : delta = 0.1 - 2*(0.08+2*0.02) = 0.1 - 2*0.12 = 0.1-0.24 = -0.14."""
        card = self._base_card()
        result = review_card(card, 3)
        assert result.ef == round(2.5 - 0.14, 4)  # 2.36

    def test_ef_clamped_to_minimum(self):
        """EF ne descend jamais sous EF_MIN (1.3)."""
        # Créer une carte avec ef très bas et quality=3 plusieurs fois
        card = SRSCard(
            id="test", fen="f", solution="s",
            ef=EF_MIN, interval=1, reps=0,
            due=date.today().isoformat(),
        )
        result = review_card(card, 3)
        assert result.ef >= EF_MIN

    def test_due_date_is_today_plus_interval(self):
        card = self._base_card()
        result = review_card(card, 4)  # interval=1
        assert result.due == (date.today() + timedelta(days=1)).isoformat()

    def test_due_date_second_rep(self):
        card = self._base_card()
        card = review_card(card, 4)  # reps=1, interval=1, due=today+1
        card = review_card(card, 4)  # reps=2, interval=6
        expected_due = (date.today() + timedelta(days=6)).isoformat()
        assert card.due == expected_due

    def test_interval_minimum_is_1(self):
        """L'intervalle ne descend jamais sous 1."""
        card = SRSCard(
            id="test", fen="f", solution="s",
            ef=EF_MIN, interval=1, reps=2,
            due=date.today().isoformat(),
        )
        result = review_card(card, 3)  # reps=3, interval = max(1, round(1 * ef))
        assert result.interval >= 1


# ===================================================================
# get_due_cards
# ===================================================================

class TestGetDueCards:
    """Tests pour get_due_cards(cards, reference_date)."""

    def test_empty_list_returns_empty(self):
        assert get_due_cards([]) == []

    def test_overdue_card_returned(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        card = SRSCard(id="1", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=yesterday)
        due = get_due_cards([card])
        assert len(due) == 1

    def test_today_card_returned(self):
        card = SRSCard(id="1", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=date.today().isoformat())
        due = get_due_cards([card])
        assert len(due) == 1

    def test_future_card_not_returned(self):
        tomorrow = (date.today() + timedelta(days=2)).isoformat()
        card = SRSCard(id="1", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=tomorrow)
        due = get_due_cards([card])
        assert len(due) == 0

    def test_sorts_by_due_date(self):
        far = (date.today() + timedelta(days=5)).isoformat()
        near = (date.today() - timedelta(days=2)).isoformat()
        mid = date.today().isoformat()
        c1 = SRSCard(id="1", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=far)
        c2 = SRSCard(id="2", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=near)
        c3 = SRSCard(id="3", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=mid)
        due = get_due_cards([c1, c2, c3])
        ids = [c.id for c in due]
        assert ids == ["2", "3"]

    def test_custom_reference_date(self):
        ref = date.today() + timedelta(days=10)
        card = SRSCard(id="1", fen="f", solution="s", ef=2.5, interval=1, reps=0,
                        due=(date.today() + timedelta(days=5)).isoformat())
        due = get_due_cards([card], reference_date=ref)
        assert len(due) == 1

    def test_multiple_overdue_sorted(self):
        d1 = (date.today() - timedelta(days=10)).isoformat()
        d2 = (date.today() - timedelta(days=1)).isoformat()
        d3 = (date.today() - timedelta(days=5)).isoformat()
        c1 = SRSCard(id="a", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=d1)
        c2 = SRSCard(id="b", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=d2)
        c3 = SRSCard(id="c", fen="f", solution="s", ef=2.5, interval=1, reps=0, due=d3)
        due = get_due_cards([c1, c2, c3])
        assert [c.id for c in due] == ["a", "c", "b"]
