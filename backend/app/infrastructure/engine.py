"""Abstraction du moteur d'évaluation — EPIC 2.

L'analyse a besoin d'évaluations Stockfish (profondeur fixe = 14). Deux sources
sont possibles selon le déploiement ; elles sont unifiées derrière le protocole
``EngineProvider`` pour que la couche domaine (ACPL, tactique/stratégie) reste
pure et testable, indépendamment de l'origine des évaluations.

* ``ClientProvidedEngine`` — actif aujourd'hui : le frontend possède déjà
  Stockfish WASM, calcule les évaluations coup par coup et les transmet au
  backend, qui se contente de les relire.
* ``NativeStockfishEngine`` — branchable plus tard sur Render : appelle un
  binaire Stockfish natif via ``chess.engine``. Importé paresseusement pour ne
  pas exiger le binaire dans les environnements de test.

Convention de signe : tous les scores sont en centipions **du point de vue du
camp au trait** (positif = avantage pour celui qui doit jouer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:  # pragma: no cover - typing helper
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

#: Profondeur d'analyse fixe imposée par la spécification (US 2.2).
ENGINE_DEPTH: int = 14

#: Score conventionnel (cp) attribué à un mat, du point de vue du camp gagnant.
MATE_SCORE: int = 100_000


@dataclass(frozen=True)
class MoveScore:
    """Évaluation d'un coup candidat (une ligne du multipv)."""
    move_uci: str
    score_cp: int  # centipions, point de vue du camp au trait
    is_mate: bool = False
    mate_in: Optional[int] = None


@dataclass(frozen=True)
class PositionEval:
    """Évaluation d'une position : lignes multipv triées du meilleur au pire."""
    fen: str
    lines: List[MoveScore] = field(default_factory=list)

    @property
    def best(self) -> Optional[MoveScore]:
        """Meilleure ligne (ou ``None`` si aucune)."""
        return self.lines[0] if self.lines else None

    def score_of(self, move_uci: str) -> Optional[int]:
        """Score (cp) d'un coup donné s'il figure dans le multipv, sinon ``None``."""
        for line in self.lines:
            if line.move_uci == move_uci:
                return line.score_cp
        return None


@runtime_checkable
class EngineProvider(Protocol):
    """Contrat commun à toutes les sources d'évaluation."""

    depth: int

    def analyse(self, fen: str, multipv: int = 3) -> PositionEval:
        """Renvoie l'évaluation multipv d'une position (FEN)."""
        ...


class ClientProvidedEngine:
    """Source d'évaluations pré-calculées (par le Stockfish du navigateur).

    Les évaluations, indexées par FEN, sont fournies à la construction. Aucune
    dépendance moteur n'est requise — idéal en production immédiate et en test.
    """

    def __init__(
        self,
        evals: Optional[Dict[str, PositionEval]] = None,
        depth: int = ENGINE_DEPTH,
    ) -> None:
        self._evals: Dict[str, PositionEval] = dict(evals or {})
        self.depth = depth

    def add(self, position: PositionEval) -> None:
        """Enregistre (ou remplace) l'évaluation d'une position."""
        self._evals[position.fen] = position

    def analyse(self, fen: str, multipv: int = 3) -> PositionEval:
        """Relit l'évaluation fournie pour ``fen``.

        Raises
        ------
        KeyError
            Si aucune évaluation n'a été fournie pour cette position.
        """
        position = self._evals.get(fen)
        if position is None:
            raise KeyError(f"Aucune évaluation fournie pour la position : {fen}")
        if multipv >= len(position.lines):
            return position
        return PositionEval(fen=position.fen, lines=position.lines[:multipv])


class NativeStockfishEngine:
    """Source d'évaluations via un binaire Stockfish natif (Render).

    L'import de ``chess.engine`` et l'ouverture du binaire sont paresseux pour
    ne pas exiger Stockfish dans les environnements dépourvus du binaire.
    """

    def __init__(self, binary_path: Optional[str], depth: int = ENGINE_DEPTH) -> None:
        self.binary_path = binary_path
        self.depth = depth
        self._engine = None  # ouvert à la 1ʳᵉ analyse

    def _ensure_engine(self):  # pragma: no cover - nécessite le binaire natif
        if self._engine is None:
            if not self.binary_path:
                raise RuntimeError(
                    "Chemin du binaire Stockfish non configuré (STOCKFISH_PATH)."
                )
            import chess.engine  # import paresseux

            self._engine = chess.engine.SimpleEngine.popen_uci(self.binary_path)
        return self._engine

    def analyse(self, fen: str, multipv: int = 3) -> PositionEval:  # pragma: no cover
        import chess
        import chess.engine

        board = chess.Board(fen)
        engine = self._ensure_engine()
        infos = engine.analyse(
            board, chess.engine.Limit(depth=self.depth), multipv=multipv
        )
        lines: List[MoveScore] = []
        for info in infos:
            pv = info.get("pv")
            move = pv[0] if pv else None
            pov = info["score"].pov(board.turn)
            lines.append(
                MoveScore(
                    move_uci=move.uci() if move else "",
                    score_cp=pov.score(mate_score=MATE_SCORE),
                    is_mate=pov.is_mate(),
                    mate_in=pov.mate(),
                )
            )
        return PositionEval(fen=fen, lines=lines)

    def close(self) -> None:  # pragma: no cover - nécessite le binaire natif
        if self._engine is not None:
            self._engine.quit()
            self._engine = None
