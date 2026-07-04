#!/usr/bin/env bash
# Lance mutmut module par module en ciblant uniquement les tests pertinents,
# pour éviter de rejouer toute la suite (964 tests) à chaque mutant.
set -uo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate

declare -A MOD_TESTS=(
  [acpl]="tests/test_acpl.py"
  [analysis_pipeline]="tests/test_analysis_pipeline.py"
  [analyzer]="tests/test_analyzer.py"
  [auth]="tests/test_auth.py tests/test_games_api.py"
  [cadence]="tests/test_cadence.py"
  [coaching_voice]="tests/test_coaching_voice.py"
  [cognitive_load]="tests/test_cognitive_load.py"
  [daily_quests]="tests/test_daily_quests.py"
  [elo_calculator]="tests/test_elo.py"
  [elo_curve]="tests/test_elo_curve.py tests/test_elo_curve_api.py"
  [endgames]="tests/test_endgames_api.py"
  [error_profile]="tests/test_error_profile.py tests/test_error_profile_api.py"
  [game_salvage]="tests/test_game_salvage.py"
  [game_sync]="tests/test_game_sync.py tests/test_games_sync_api.py"
  [gamification]="tests/test_gamification.py"
  [lichess_puzzles]="tests/test_lichess_puzzles.py"
  [move_class]="tests/test_move_class.py"
  [opening_repertoire]="tests/test_opening_repertoire.py tests/test_srs_flashcards.py"
  [phases]="tests/test_phases.py"
  [progress_history]="tests/test_progress_history.py"
  [seasons]="tests/test_seasons.py tests/test_seasons_api.py"
  [srs_engine]="tests/test_srs.py tests/test_srs_flashcards.py"
  [srs_flashcards]="tests/test_srs_flashcards.py tests/test_srs_flashcards_api.py"
  [stats_aggregator]="tests/test_stats_aggregator.py"
  [tactical_elo]="tests/test_tactical_elo.py"
  [tactical_sprint]="tests/test_tactical_sprint.py tests/test_tactical_sprint_api.py"
  [tactics]="tests/test_error_profile.py tests/test_tactics.py tests/test_tactics_api.py tests/test_tactics_fallback.py"
  [virtual_elo]="tests/test_virtual_elo.py"
)

echo "=== mutmut per-module run starting $(date) ==="

for mod in "${!MOD_TESTS[@]}"; do
  tfiles="${MOD_TESTS[$mod]}"
  echo ""
  echo ">>> Module: $mod  | tests: $tfiles"
  python -m mutmut run \
    --paths-to-mutate "app/domain/${mod}.py" \
    --runner "python -m pytest ${tfiles} -q -x" \
    --CI
  echo ">>> Done module: $mod (exit=$?)"
done

echo "=== mutmut per-module run finished $(date) ==="
