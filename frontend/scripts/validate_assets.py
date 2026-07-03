"""EPIC 18 (US 18.1) — Valide que tous les SVG de pièces requis sont présents
avant de lancer le serveur frontend, pour éviter des 404 silencieux sur
l'échiquier (astuce PO explicite : bloquer le build plutôt que découvrir le
problème dans le navigateur).

Module quasi-pur : `find_missing_assets` ne fait que de la lecture disque
(`os.path.isfile`), sans effet de bord, donc testable indépendamment de
`main`/`sys.exit`.
"""

from __future__ import annotations

import os
import sys

# Doit rester synchronisé avec `PIECE_THEMES` de `js/theme_service.js`
# (EPIC 18, US 18.1) — chaque thème listé ici doit avoir un dossier complet.
PIECE_THEMES = ("cburnett", "cyber-tactics")
PIECE_CODES = tuple(f"{color}{kind}" for color in "wb" for kind in "KQRBNP")

FRONTEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_missing_assets(base_dir: str = FRONTEND_DIR) -> list:
    """Renvoie la liste des chemins de SVG de pièces manquants (vide si tout est présent)."""
    missing = []
    for theme in PIECE_THEMES:
        for code in PIECE_CODES:
            path = os.path.join(base_dir, "assets", "pieces", theme, f"{code}.svg")
            if not os.path.isfile(path):
                missing.append(path)
    return missing


def main() -> int:
    missing = find_missing_assets()
    if missing:
        print("Assets de pièces manquants — build bloqué (EPIC 18, US 18.1) :", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 1
    print(f"OK : {len(PIECE_THEMES)} thème(s) x {len(PIECE_CODES)} pièces présents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
