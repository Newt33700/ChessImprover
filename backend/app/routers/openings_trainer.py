"""Lotus Mastery Engine — Ouvertures (EPIC 38, US 38.1).

REMPLACE l'Entraîneur d'Ouvertures EPIC 9 (répertoire de lignes + SRS SM-2 —
``POST/GET/DELETE /api/v1/openings/repertoire*``) par un arbre de positions
avec progression par nœud :

* ``POST /api/v1/openings/trainer/import``     — reconstruit l'arbre depuis un PGN.
* ``GET  /api/v1/openings/trainer/next-move``  — prochain nœud à travailler (session).
* ``POST /api/v1/openings/trainer/attempt``    — valide une tentative, applique le moteur de maîtrise.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.domain.mastery_engine import process_attempt, rank_for_score
from app.domain.models import (
    NextMoveResponse,
    OpeningAttemptRequest,
    OpeningAttemptResult,
    PGNImportRequest,
    RepertoireImportResult,
)
from app.domain.opening_repertoire import parse_pgn_tree
from app.infrastructure import db_client
from app.routers.deps import get_current_user_id

router = APIRouter(prefix="/api/v1/openings/trainer", tags=["openings"])


@router.post("/import", response_model=RepertoireImportResult)
async def import_repertoire(
    body: PGNImportRequest, user_id: str = Depends(get_current_user_id),
) -> RepertoireImportResult:
    """Reconstruit l'arbre depuis un PGN — jamais de confiance aveugle au
    client : la légalité de chaque coup est vérifiée par ``parse_pgn_tree``
    (python-chess). Règle de déblocage (US 38.1) : seuls les nœuds racines
    (``parent_id`` absent — premiers coups possibles depuis la position
    initiale) sont débloqués (statut ``learning``) ; tout le reste du reste
    verrouillé (aucune ligne dans ``user_node_progress``, jamais un statut
    ``locked`` stocké explicitement).
    """
    nodes_data = parse_pgn_tree(body.pgn)
    if not nodes_data:
        raise HTTPException(status_code=422, detail="PGN invalide ou sans coup exploitable.")

    repertoire_id = str(uuid.uuid4())
    created = db_client.create_repertoire_nodes(user_id, repertoire_id, nodes_data)
    root_ids = [node["id"] for node in created if node["parent_id"] is None]
    db_client.unlock_nodes(user_id, root_ids)

    return RepertoireImportResult(repertoire_id=repertoire_id, node_count=len(created))


@router.get("/next-move", response_model=NextMoveResponse)
async def next_move(user_id: str = Depends(get_current_user_id)) -> NextMoveResponse:
    """Générateur de sessions (US 38.1) — priorité stricte : révision en
    retard (``review`` + échéance dépassée) d'abord, puis nouvelles lignes
    débloquées (``learning``). ``session_complete: true`` si rien n'est dû
    ni à apprendre. La solution (``move_san``) n'est jamais exposée ici —
    seule la position de départ (``fen``), validée via ``POST /attempt``.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    entry = db_client.get_next_training_node(user_id, now_iso)
    if entry is None:
        return NextMoveResponse(session_complete=True)

    return NextMoveResponse(
        session_complete=False,
        node_id=entry["node_id"],
        fen=entry["from_fen"],
        depth_level=entry["depth_level"],
        is_mainline=entry["is_mainline"],
        status=entry["status"],
        mastery_score=entry["mastery_score"],
        rank=rank_for_score(entry["mastery_score"]),
    )


@router.post("/attempt", response_model=OpeningAttemptResult)
async def submit_attempt(
    body: OpeningAttemptRequest, user_id: str = Depends(get_current_user_id),
) -> OpeningAttemptResult:
    """Valide le coup joué **côté serveur** contre ``move_san`` (jamais une
    confiance aveugle au client, même politique anti-triche que le Coach
    Tactique) puis applique le moteur de maîtrise (``domain.mastery_engine.
    process_attempt``) : ``+15``/``srs_interval`` doublé en cas de succès,
    ``-20``/``srs_interval`` remis à 1 jour en cas d'échec, déblocage des
    nœuds enfants directs si le score franchit le seuil Intermediate (40).
    """
    node = db_client.get_repertoire_node(body.node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Nœud introuvable.")
    progress = db_client.get_node_progress(user_id, body.node_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Nœud non débloqué pour cet utilisateur.")

    is_success = body.move_san == node["move_san"]
    result = process_attempt(progress["mastery_score"], progress["srs_interval"], is_success)
    db_client.update_node_progress(
        user_id, body.node_id, result["mastery_score"], result["srs_interval"],
        result["status"], result["next_review_date"].isoformat(),
    )

    unlocked_children = 0
    if result["should_unlock_children"]:
        children = db_client.get_direct_children(body.node_id)
        unlocked_children = db_client.unlock_nodes(user_id, [c["id"] for c in children])

    return OpeningAttemptResult(
        node_id=body.node_id,
        status=result["status"],
        mastery_score=result["mastery_score"],
        srs_interval=result["srs_interval"],
        rank=result["rank"],
        unlocked_children=unlocked_children,
    )
