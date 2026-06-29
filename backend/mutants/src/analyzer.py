
from inspect import signature as _mutmut_signature

def _mutmut_trampoline(orig, mutants, *args, **kwargs):
    import os
    mutant_under_test = os.environ['MUTANT_UNDER_TEST']
    if mutant_under_test == 'fail':
        from __main__ import MutmutProgrammaticFailException
        raise MutmutProgrammaticFailException('Failed programmatically')      
    elif mutant_under_test == 'stats':
        from __main__ import record_trampoline_hit
        record_trampoline_hit(orig.__module__ + '.' + orig.__name__)
        return orig(*args, **kwargs)
    prefix = orig.__module__ + '.' + orig.__name__ + '__mutmut_'
    if not mutant_under_test.startswith(prefix):
        return orig(*args, **kwargs)
    mutant_name = mutant_under_test.rpartition('.')[-1]
    return mutants[mutant_name](*args, **kwargs)


"""Moteur de règles géométriques — analyse PGN sans moteur d'échecs.

Détecte les failles évidentes du débutant à partir du PGN textuel :
  - Blunders (pièces données en 1 coup, non défendues)
  - Fourchettes manquées (pion/cavalier attaquant 2 pièces adverses de
    valeur supérieure, mais non jouées)
  - Zeitnot (panique temporelle : chute > 50 % du temps sur un coup = gaffe)

La bibliothèque ``python-chess`` sert uniquement à manipuler les positions ;
l'analyse elle-même est pure et testable (Clean Architecture : couche domaine).
"""

from __future__ import annotations

import io as _io
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import chess
import chess.pgn


# ---------------------------------------------------------------------------
# Structures de sortie
# ---------------------------------------------------------------------------

@dataclass
class GeometricReport:
    """Résultat de l'analyse géométrique d'une partie."""
    blunders_count: int = 0
    missed_forks_count: int = 0
    time_panic_count: int = 0
    blunder_moves: List[str] = field(default_factory=list)
    missed_fork_moves: List[str] = field(default_factory=list)
    time_panic_moves: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constantes internes
# ---------------------------------------------------------------------------

# Valeur matérielle standard des pièces (en centipions).
PIECE_VALUES: dict = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Seuil de chute de temps pour la zeitnot : > 50 % sur un seul coup.
TIME_PANIC_RATIO: float = 0.5

# Regex pour extraire les balises [%clk H:MM:SS] du PGN.
_CLK_PATTERN: re.Pattern = re.compile(r"\[%clk\s+(\d{1,2}):(\d{2}):(\d{2})\]")


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_orig(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_1(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split("XX:XX")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_2(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = None
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_3(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) != 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_4(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 4:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_5(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = None
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_6(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(None) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_7(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) / 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_8(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3601 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_9(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 - int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_10(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(None) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_11(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) / 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_12(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 61 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_13(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 - float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_14(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(None)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_15(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) != 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_16(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 3:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_17(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = None
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_18(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(None) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_19(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) / 60 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_20(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 61 + float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_21(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 - float(secs)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_22(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(None)
    except ValueError:
        return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_23(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def parse_clk__mutmut_24(clk_str: str) -> float:
    """Convertit une horloge PGN en secondes.

    Accepte ``H:MM:SS`` ou ``MM:SS``. Retourne 0.0 si le format est invalide.
    """
    parts = clk_str.strip().split(":")
    try:
        if len(parts) == 3:
            hours, mins, secs = parts
            return int(hours) * 3600 + int(mins) * 60 + float(secs)
        if len(parts) == 2:
            mins, secs = parts
            return int(mins) * 60 + float(secs)
    except ValueError:
        return 0.0
    return 1.0

parse_clk__mutmut_mutants = {
'parse_clk__mutmut_1': parse_clk__mutmut_1, 
    'parse_clk__mutmut_2': parse_clk__mutmut_2, 
    'parse_clk__mutmut_3': parse_clk__mutmut_3, 
    'parse_clk__mutmut_4': parse_clk__mutmut_4, 
    'parse_clk__mutmut_5': parse_clk__mutmut_5, 
    'parse_clk__mutmut_6': parse_clk__mutmut_6, 
    'parse_clk__mutmut_7': parse_clk__mutmut_7, 
    'parse_clk__mutmut_8': parse_clk__mutmut_8, 
    'parse_clk__mutmut_9': parse_clk__mutmut_9, 
    'parse_clk__mutmut_10': parse_clk__mutmut_10, 
    'parse_clk__mutmut_11': parse_clk__mutmut_11, 
    'parse_clk__mutmut_12': parse_clk__mutmut_12, 
    'parse_clk__mutmut_13': parse_clk__mutmut_13, 
    'parse_clk__mutmut_14': parse_clk__mutmut_14, 
    'parse_clk__mutmut_15': parse_clk__mutmut_15, 
    'parse_clk__mutmut_16': parse_clk__mutmut_16, 
    'parse_clk__mutmut_17': parse_clk__mutmut_17, 
    'parse_clk__mutmut_18': parse_clk__mutmut_18, 
    'parse_clk__mutmut_19': parse_clk__mutmut_19, 
    'parse_clk__mutmut_20': parse_clk__mutmut_20, 
    'parse_clk__mutmut_21': parse_clk__mutmut_21, 
    'parse_clk__mutmut_22': parse_clk__mutmut_22, 
    'parse_clk__mutmut_23': parse_clk__mutmut_23, 
    'parse_clk__mutmut_24': parse_clk__mutmut_24
}

def parse_clk(*args, **kwargs):
    return _mutmut_trampoline(parse_clk__mutmut_orig, parse_clk__mutmut_mutants, *args, **kwargs) 

parse_clk.__signature__ = _mutmut_signature(parse_clk__mutmut_orig)
parse_clk__mutmut_orig.__name__ = 'parse_clk'




def extract_comment_clock__mutmut_orig(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if not match:
        return None
    clk_str = f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_1(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if  comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if not match:
        return None
    clk_str = f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_2(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(None)
    if not match:
        return None
    clk_str = f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_3(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = None
    if not match:
        return None
    clk_str = f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_4(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if  match:
        return None
    clk_str = f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_5(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if not match:
        return None
    clk_str = f"{match.group(2)}:{match.group(2)}:{match.group(3)}"
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_6(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if not match:
        return None
    clk_str = f"{match.group(1)}:{match.group(3)}:{match.group(3)}"
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_7(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if not match:
        return None
    clk_str = f"{match.group(1)}:{match.group(2)}:{match.group(4)}"
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_8(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if not match:
        return None
    clk_str = None
    return parse_clk(clk_str)


def extract_comment_clock__mutmut_9(comment: str) -> Optional[float]:
    """Extrait l'horloge d'un commentaire PGN, ou ``None`` si absent."""
    if not comment:
        return None
    match = _CLK_PATTERN.search(comment)
    if not match:
        return None
    clk_str = f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
    return parse_clk(None)

extract_comment_clock__mutmut_mutants = {
'extract_comment_clock__mutmut_1': extract_comment_clock__mutmut_1, 
    'extract_comment_clock__mutmut_2': extract_comment_clock__mutmut_2, 
    'extract_comment_clock__mutmut_3': extract_comment_clock__mutmut_3, 
    'extract_comment_clock__mutmut_4': extract_comment_clock__mutmut_4, 
    'extract_comment_clock__mutmut_5': extract_comment_clock__mutmut_5, 
    'extract_comment_clock__mutmut_6': extract_comment_clock__mutmut_6, 
    'extract_comment_clock__mutmut_7': extract_comment_clock__mutmut_7, 
    'extract_comment_clock__mutmut_8': extract_comment_clock__mutmut_8, 
    'extract_comment_clock__mutmut_9': extract_comment_clock__mutmut_9
}

def extract_comment_clock(*args, **kwargs):
    return _mutmut_trampoline(extract_comment_clock__mutmut_orig, extract_comment_clock__mutmut_mutants, *args, **kwargs) 

extract_comment_clock.__signature__ = _mutmut_signature(extract_comment_clock__mutmut_orig)
extract_comment_clock__mutmut_orig.__name__ = 'extract_comment_clock'




def is_piece_hanging__mutmut_orig(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = board.is_attacked_by(player_color, square)
    return attacked and not defended


def is_piece_hanging__mutmut_1(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by( player_color, square)
    defended = board.is_attacked_by(player_color, square)
    return attacked and not defended


def is_piece_hanging__mutmut_2(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, None)
    defended = board.is_attacked_by(player_color, square)
    return attacked and not defended


def is_piece_hanging__mutmut_3(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color,)
    defended = board.is_attacked_by(player_color, square)
    return attacked and not defended


def is_piece_hanging__mutmut_4(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = None
    defended = board.is_attacked_by(player_color, square)
    return attacked and not defended


def is_piece_hanging__mutmut_5(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = board.is_attacked_by(None, square)
    return attacked and not defended


def is_piece_hanging__mutmut_6(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = board.is_attacked_by(player_color, None)
    return attacked and not defended


def is_piece_hanging__mutmut_7(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = board.is_attacked_by( square)
    return attacked and not defended


def is_piece_hanging__mutmut_8(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = board.is_attacked_by(player_color,)
    return attacked and not defended


def is_piece_hanging__mutmut_9(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = None
    return attacked and not defended


def is_piece_hanging__mutmut_10(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = board.is_attacked_by(player_color, square)
    return attacked and  defended


def is_piece_hanging__mutmut_11(
    board: chess.Board, square: chess.Square, player_color: chess.Color
) -> bool:
    """Vrai si la pièce du joueur sur ``square`` est attaquée et NON défendue.

    Une pièce "pendante" (hanging) = cadeau en 1 coup : attaquée par
    l'adversaire mais protégée par aucune pièce alliée.
    """
    attacked = board.is_attacked_by(not player_color, square)
    defended = board.is_attacked_by(player_color, square)
    return attacked or not defended

is_piece_hanging__mutmut_mutants = {
'is_piece_hanging__mutmut_1': is_piece_hanging__mutmut_1, 
    'is_piece_hanging__mutmut_2': is_piece_hanging__mutmut_2, 
    'is_piece_hanging__mutmut_3': is_piece_hanging__mutmut_3, 
    'is_piece_hanging__mutmut_4': is_piece_hanging__mutmut_4, 
    'is_piece_hanging__mutmut_5': is_piece_hanging__mutmut_5, 
    'is_piece_hanging__mutmut_6': is_piece_hanging__mutmut_6, 
    'is_piece_hanging__mutmut_7': is_piece_hanging__mutmut_7, 
    'is_piece_hanging__mutmut_8': is_piece_hanging__mutmut_8, 
    'is_piece_hanging__mutmut_9': is_piece_hanging__mutmut_9, 
    'is_piece_hanging__mutmut_10': is_piece_hanging__mutmut_10, 
    'is_piece_hanging__mutmut_11': is_piece_hanging__mutmut_11
}

def is_piece_hanging(*args, **kwargs):
    return _mutmut_trampoline(is_piece_hanging__mutmut_orig, is_piece_hanging__mutmut_mutants, *args, **kwargs) 

is_piece_hanging.__signature__ = _mutmut_signature(is_piece_hanging__mutmut_orig)
is_piece_hanging__mutmut_orig.__name__ = 'is_piece_hanging'




def _target_is_high_value__mutmut_orig(target: chess.Piece, forking_value: int) -> bool:
    """Vrai si une pièce adverse mérite d'être comptée dans une fourchette.

    Le roi compte toujours (force une réponse) ; sinon il faut que la valeur
    matérielle de la cible soit strictement supérieure à celle de la pièce qui
    fourchette (gain matériel potentiel).
    """
    if target.piece_type == chess.KING:
        return True
    return PIECE_VALUES[target.piece_type] > forking_value


def _target_is_high_value__mutmut_1(target: chess.Piece, forking_value: int) -> bool:
    """Vrai si une pièce adverse mérite d'être comptée dans une fourchette.

    Le roi compte toujours (force une réponse) ; sinon il faut que la valeur
    matérielle de la cible soit strictement supérieure à celle de la pièce qui
    fourchette (gain matériel potentiel).
    """
    if target.piece_type != chess.KING:
        return True
    return PIECE_VALUES[target.piece_type] > forking_value


def _target_is_high_value__mutmut_2(target: chess.Piece, forking_value: int) -> bool:
    """Vrai si une pièce adverse mérite d'être comptée dans une fourchette.

    Le roi compte toujours (force une réponse) ; sinon il faut que la valeur
    matérielle de la cible soit strictement supérieure à celle de la pièce qui
    fourchette (gain matériel potentiel).
    """
    if target.piece_type == chess.KING:
        return False
    return PIECE_VALUES[target.piece_type] > forking_value


def _target_is_high_value__mutmut_3(target: chess.Piece, forking_value: int) -> bool:
    """Vrai si une pièce adverse mérite d'être comptée dans une fourchette.

    Le roi compte toujours (force une réponse) ; sinon il faut que la valeur
    matérielle de la cible soit strictement supérieure à celle de la pièce qui
    fourchette (gain matériel potentiel).
    """
    if target.piece_type == chess.KING:
        return True
    return PIECE_VALUES[None] > forking_value


def _target_is_high_value__mutmut_4(target: chess.Piece, forking_value: int) -> bool:
    """Vrai si une pièce adverse mérite d'être comptée dans une fourchette.

    Le roi compte toujours (force une réponse) ; sinon il faut que la valeur
    matérielle de la cible soit strictement supérieure à celle de la pièce qui
    fourchette (gain matériel potentiel).
    """
    if target.piece_type == chess.KING:
        return True
    return PIECE_VALUES[target.piece_type] >= forking_value

_target_is_high_value__mutmut_mutants = {
'_target_is_high_value__mutmut_1': _target_is_high_value__mutmut_1, 
    '_target_is_high_value__mutmut_2': _target_is_high_value__mutmut_2, 
    '_target_is_high_value__mutmut_3': _target_is_high_value__mutmut_3, 
    '_target_is_high_value__mutmut_4': _target_is_high_value__mutmut_4
}

def _target_is_high_value(*args, **kwargs):
    return _mutmut_trampoline(_target_is_high_value__mutmut_orig, _target_is_high_value__mutmut_mutants, *args, **kwargs) 

_target_is_high_value.__signature__ = _mutmut_signature(_target_is_high_value__mutmut_orig)
_target_is_high_value__mutmut_orig.__name__ = '_target_is_high_value'




def find_fork_moves__mutmut_orig(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_1(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = None
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_2(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = None
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_3(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type  in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_4(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[None]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_5(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = None
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_6(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(None)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_7(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = None
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_8(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 1
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_9(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = None
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_10(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(None)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_11(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = None
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_12(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is  None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_13(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color == player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_14(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None or target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_15(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(None, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_16(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, None):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_17(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value( forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_18(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target,):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_19(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets -= 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_20(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets = 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_21(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 2

        board.pop()

        if high_value_targets >= 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_22(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets > 2:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_23(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 3:
            forks.append(move)

    return forks


def find_fork_moves__mutmut_24(
    board: chess.Board, player_color: chess.Color
) -> List[chess.Move]:
    """Liste les coups de fourchette (pion ou cavalier) disponibles.

    Une fourchette est un coup de pion ou de cavalier qui, une fois joué,
    attaque simultanément au moins deux pièces adverses de valeur supérieure.
    """
    forks: List[chess.Move] = []
    for move in board.legal_moves:
        piece_type = board.piece_type_at(move.from_square)
        if piece_type not in (chess.PAWN, chess.KNIGHT):
            continue

        forking_value = PIECE_VALUES[piece_type]
        board.push(move)

        # Squares attaqués PAR LA PIÈCE DÉPLACÉE uniquement.
        attacked_squares = board.attacks(move.to_square)
        high_value_targets = 0
        for sq in attacked_squares:
            target = board.piece_at(sq)
            if target is not None and target.color != player_color:
                if _target_is_high_value(target, forking_value):
                    high_value_targets += 1

        board.pop()

        if high_value_targets >= 2:
            forks.append(None)

    return forks

find_fork_moves__mutmut_mutants = {
'find_fork_moves__mutmut_1': find_fork_moves__mutmut_1, 
    'find_fork_moves__mutmut_2': find_fork_moves__mutmut_2, 
    'find_fork_moves__mutmut_3': find_fork_moves__mutmut_3, 
    'find_fork_moves__mutmut_4': find_fork_moves__mutmut_4, 
    'find_fork_moves__mutmut_5': find_fork_moves__mutmut_5, 
    'find_fork_moves__mutmut_6': find_fork_moves__mutmut_6, 
    'find_fork_moves__mutmut_7': find_fork_moves__mutmut_7, 
    'find_fork_moves__mutmut_8': find_fork_moves__mutmut_8, 
    'find_fork_moves__mutmut_9': find_fork_moves__mutmut_9, 
    'find_fork_moves__mutmut_10': find_fork_moves__mutmut_10, 
    'find_fork_moves__mutmut_11': find_fork_moves__mutmut_11, 
    'find_fork_moves__mutmut_12': find_fork_moves__mutmut_12, 
    'find_fork_moves__mutmut_13': find_fork_moves__mutmut_13, 
    'find_fork_moves__mutmut_14': find_fork_moves__mutmut_14, 
    'find_fork_moves__mutmut_15': find_fork_moves__mutmut_15, 
    'find_fork_moves__mutmut_16': find_fork_moves__mutmut_16, 
    'find_fork_moves__mutmut_17': find_fork_moves__mutmut_17, 
    'find_fork_moves__mutmut_18': find_fork_moves__mutmut_18, 
    'find_fork_moves__mutmut_19': find_fork_moves__mutmut_19, 
    'find_fork_moves__mutmut_20': find_fork_moves__mutmut_20, 
    'find_fork_moves__mutmut_21': find_fork_moves__mutmut_21, 
    'find_fork_moves__mutmut_22': find_fork_moves__mutmut_22, 
    'find_fork_moves__mutmut_23': find_fork_moves__mutmut_23, 
    'find_fork_moves__mutmut_24': find_fork_moves__mutmut_24
}

def find_fork_moves(*args, **kwargs):
    return _mutmut_trampoline(find_fork_moves__mutmut_orig, find_fork_moves__mutmut_mutants, *args, **kwargs) 

find_fork_moves.__signature__ = _mutmut_signature(find_fork_moves__mutmut_orig)
find_fork_moves__mutmut_orig.__name__ = 'find_fork_moves'




def _read_mainline_clocks__mutmut_orig(
    game: chess.pgn.Game,
) -> List[Optional[float]]:
    """Construit la liste des horloges après chaque coup de la ligne principale.

    L'index ``i`` correspond au i-ème coup (0-based). ``None`` si pas de balise.
    """
    clocks: List[Optional[float]] = []
    node = game
    while node.variations:
        child = node.variations[0]
        clocks.append(extract_comment_clock(child.comment))
        node = child
    return clocks


def _read_mainline_clocks__mutmut_1(
    game: chess.pgn.Game,
) -> List[Optional[float]]:
    """Construit la liste des horloges après chaque coup de la ligne principale.

    L'index ``i`` correspond au i-ème coup (0-based). ``None`` si pas de balise.
    """
    clocks: List[Optional[float]] = None
    node = game
    while node.variations:
        child = node.variations[0]
        clocks.append(extract_comment_clock(child.comment))
        node = child
    return clocks


def _read_mainline_clocks__mutmut_2(
    game: chess.pgn.Game,
) -> List[Optional[float]]:
    """Construit la liste des horloges après chaque coup de la ligne principale.

    L'index ``i`` correspond au i-ème coup (0-based). ``None`` si pas de balise.
    """
    clocks: List[Optional[float]] = []
    node = None
    while node.variations:
        child = node.variations[0]
        clocks.append(extract_comment_clock(child.comment))
        node = child
    return clocks


def _read_mainline_clocks__mutmut_3(
    game: chess.pgn.Game,
) -> List[Optional[float]]:
    """Construit la liste des horloges après chaque coup de la ligne principale.

    L'index ``i`` correspond au i-ème coup (0-based). ``None`` si pas de balise.
    """
    clocks: List[Optional[float]] = []
    node = game
    while node.variations:
        child = node.variations[1]
        clocks.append(extract_comment_clock(child.comment))
        node = child
    return clocks


def _read_mainline_clocks__mutmut_4(
    game: chess.pgn.Game,
) -> List[Optional[float]]:
    """Construit la liste des horloges après chaque coup de la ligne principale.

    L'index ``i`` correspond au i-ème coup (0-based). ``None`` si pas de balise.
    """
    clocks: List[Optional[float]] = []
    node = game
    while node.variations:
        child = node.variations[None]
        clocks.append(extract_comment_clock(child.comment))
        node = child
    return clocks


def _read_mainline_clocks__mutmut_5(
    game: chess.pgn.Game,
) -> List[Optional[float]]:
    """Construit la liste des horloges après chaque coup de la ligne principale.

    L'index ``i`` correspond au i-ème coup (0-based). ``None`` si pas de balise.
    """
    clocks: List[Optional[float]] = []
    node = game
    while node.variations:
        child = None
        clocks.append(extract_comment_clock(child.comment))
        node = child
    return clocks


def _read_mainline_clocks__mutmut_6(
    game: chess.pgn.Game,
) -> List[Optional[float]]:
    """Construit la liste des horloges après chaque coup de la ligne principale.

    L'index ``i`` correspond au i-ème coup (0-based). ``None`` si pas de balise.
    """
    clocks: List[Optional[float]] = []
    node = game
    while node.variations:
        child = node.variations[0]
        clocks.append(extract_comment_clock(child.comment))
        node = None
    return clocks

_read_mainline_clocks__mutmut_mutants = {
'_read_mainline_clocks__mutmut_1': _read_mainline_clocks__mutmut_1, 
    '_read_mainline_clocks__mutmut_2': _read_mainline_clocks__mutmut_2, 
    '_read_mainline_clocks__mutmut_3': _read_mainline_clocks__mutmut_3, 
    '_read_mainline_clocks__mutmut_4': _read_mainline_clocks__mutmut_4, 
    '_read_mainline_clocks__mutmut_5': _read_mainline_clocks__mutmut_5, 
    '_read_mainline_clocks__mutmut_6': _read_mainline_clocks__mutmut_6
}

def _read_mainline_clocks(*args, **kwargs):
    return _mutmut_trampoline(_read_mainline_clocks__mutmut_orig, _read_mainline_clocks__mutmut_mutants, *args, **kwargs) 

_read_mainline_clocks.__signature__ = _mutmut_signature(_read_mainline_clocks__mutmut_orig)
_read_mainline_clocks__mutmut_orig.__name__ = '_read_mainline_clocks'




# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_orig(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_1(pgn: str, player_color: str = "XXwXX") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_2(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = None

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_3(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(None))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_4(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = None
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_5(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is not None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_6(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color != "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_7(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "XXwXX" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_8(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = None
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_9(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = None
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_10(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = None

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_11(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(None)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_12(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = None
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_13(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = ""  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_14(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 1
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_15(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = None
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_16(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[1]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_17(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[None]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_18(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = None
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_19(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = None
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_20(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is not None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_21(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = None
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_22(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn != color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_23(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = None
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_24(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[None] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_25(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index <= len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_26(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_27(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = None
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_28(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is  None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_29(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type == chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_30(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None or moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_31(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(None)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_32(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(None, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_33(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, None):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_34(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging( move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_35(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square,):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_36(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count -= 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_37(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count = 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_38(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 2
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_39(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(None, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_40(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, None)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_41(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves( color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_42(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board,)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_43(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = None
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_44(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci()  in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_45(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks or move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_46(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count -= 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_47(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count = 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_48(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 2
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_49(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = None
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_50(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = True
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_51(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = None
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_52(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is  None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_53(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type == chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_54(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None or moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_55(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(None)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_56(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(None, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_57(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, None)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_58(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging( move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_59(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square,)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_60(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = None
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_61(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is  None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_62(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is  None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_63(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before >= 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_64(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 1
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_65(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder or player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_66(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before + clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_67(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) * player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_68(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = None
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_69(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio >= TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_70(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count -= 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_71(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count = 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_72(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 2
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_73(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is  None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_74(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move or clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_75(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = None

        board.push(move)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_76(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(None)
        node = child
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_77(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = None
        move_index += 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_78(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index -= 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_79(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index = 1

    return report


# ---------------------------------------------------------------------------
# Analyse principale
# ---------------------------------------------------------------------------

def analyze_pgn__mutmut_80(pgn: str, player_color: str = "w") -> GeometricReport:
    """Analyse géométrique complète d'un PGN.

    Parameters
    ----------
    pgn : str
        Texte PGN complet (avec ou sans balises ``[%clk]``).
    player_color : str
        Couleur analysée (``'w'`` ou ``'b'``). Défaut : ``'w'``.

    Returns
    -------
    GeometricReport
        Rapport contenant les compteurs de blunders, fourchettes manquées
        et paniques temporelles. Un PGN invalide renvoie un rapport vide.
    """
    report = GeometricReport()

    try:
        game = chess.pgn.read_game(_io.StringIO(pgn))
    except Exception:
        return report
    if game is None:
        return report

    color = chess.WHITE if player_color == "w" else chess.BLACK
    board = game.board()
    node = game

    clocks = _read_mainline_clocks(game)
    player_clock_before: Optional[float] = None  # horloge du joueur avant son coup

    move_index = 0
    while node.variations:
        child = node.variations[0]
        move = child.move
        if move is None:
            node = child
            continue

        is_player_move = board.turn == color
        clk_after = clocks[move_index] if move_index < len(clocks) else None

        # --- Blunder : pièce non-pion laissée en prise non défendue ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                if is_piece_hanging(board, move.to_square, color):
                    report.blunders_count += 1
                    report.blunder_moves.append(move.uci())
                board.pop()

        # --- Fourchette manquée ---
        if is_player_move:
            forks = find_fork_moves(board, color)
            if forks and move.uci() not in {f.uci() for f in forks}:
                report.missed_forks_count += 1
                report.missed_fork_moves.append(move.uci())

        # --- Zeitnot : chute > 50 % du temps du joueur sur un coup = gaffe ---
        if is_player_move:
            moved_type = board.piece_type_at(move.from_square)
            move_is_blunder = False
            if moved_type is not None and moved_type != chess.PAWN:
                board.push(move)
                move_is_blunder = is_piece_hanging(board, move.to_square, color)
                board.pop()

            if (
                move_is_blunder
                and player_clock_before is not None
                and clk_after is not None
                and player_clock_before > 0
            ):
                drop_ratio = (player_clock_before - clk_after) / player_clock_before
                if drop_ratio > TIME_PANIC_RATIO:
                    report.time_panic_count += 1
                    report.time_panic_moves.append(move.uci())

        # Mettre à jour l'horloge du joueur après qu'il a joué.
        if is_player_move and clk_after is not None:
            player_clock_before = clk_after

        board.push(move)
        node = child
        move_index += 2

    return report

analyze_pgn__mutmut_mutants = {
'analyze_pgn__mutmut_1': analyze_pgn__mutmut_1, 
    'analyze_pgn__mutmut_2': analyze_pgn__mutmut_2, 
    'analyze_pgn__mutmut_3': analyze_pgn__mutmut_3, 
    'analyze_pgn__mutmut_4': analyze_pgn__mutmut_4, 
    'analyze_pgn__mutmut_5': analyze_pgn__mutmut_5, 
    'analyze_pgn__mutmut_6': analyze_pgn__mutmut_6, 
    'analyze_pgn__mutmut_7': analyze_pgn__mutmut_7, 
    'analyze_pgn__mutmut_8': analyze_pgn__mutmut_8, 
    'analyze_pgn__mutmut_9': analyze_pgn__mutmut_9, 
    'analyze_pgn__mutmut_10': analyze_pgn__mutmut_10, 
    'analyze_pgn__mutmut_11': analyze_pgn__mutmut_11, 
    'analyze_pgn__mutmut_12': analyze_pgn__mutmut_12, 
    'analyze_pgn__mutmut_13': analyze_pgn__mutmut_13, 
    'analyze_pgn__mutmut_14': analyze_pgn__mutmut_14, 
    'analyze_pgn__mutmut_15': analyze_pgn__mutmut_15, 
    'analyze_pgn__mutmut_16': analyze_pgn__mutmut_16, 
    'analyze_pgn__mutmut_17': analyze_pgn__mutmut_17, 
    'analyze_pgn__mutmut_18': analyze_pgn__mutmut_18, 
    'analyze_pgn__mutmut_19': analyze_pgn__mutmut_19, 
    'analyze_pgn__mutmut_20': analyze_pgn__mutmut_20, 
    'analyze_pgn__mutmut_21': analyze_pgn__mutmut_21, 
    'analyze_pgn__mutmut_22': analyze_pgn__mutmut_22, 
    'analyze_pgn__mutmut_23': analyze_pgn__mutmut_23, 
    'analyze_pgn__mutmut_24': analyze_pgn__mutmut_24, 
    'analyze_pgn__mutmut_25': analyze_pgn__mutmut_25, 
    'analyze_pgn__mutmut_26': analyze_pgn__mutmut_26, 
    'analyze_pgn__mutmut_27': analyze_pgn__mutmut_27, 
    'analyze_pgn__mutmut_28': analyze_pgn__mutmut_28, 
    'analyze_pgn__mutmut_29': analyze_pgn__mutmut_29, 
    'analyze_pgn__mutmut_30': analyze_pgn__mutmut_30, 
    'analyze_pgn__mutmut_31': analyze_pgn__mutmut_31, 
    'analyze_pgn__mutmut_32': analyze_pgn__mutmut_32, 
    'analyze_pgn__mutmut_33': analyze_pgn__mutmut_33, 
    'analyze_pgn__mutmut_34': analyze_pgn__mutmut_34, 
    'analyze_pgn__mutmut_35': analyze_pgn__mutmut_35, 
    'analyze_pgn__mutmut_36': analyze_pgn__mutmut_36, 
    'analyze_pgn__mutmut_37': analyze_pgn__mutmut_37, 
    'analyze_pgn__mutmut_38': analyze_pgn__mutmut_38, 
    'analyze_pgn__mutmut_39': analyze_pgn__mutmut_39, 
    'analyze_pgn__mutmut_40': analyze_pgn__mutmut_40, 
    'analyze_pgn__mutmut_41': analyze_pgn__mutmut_41, 
    'analyze_pgn__mutmut_42': analyze_pgn__mutmut_42, 
    'analyze_pgn__mutmut_43': analyze_pgn__mutmut_43, 
    'analyze_pgn__mutmut_44': analyze_pgn__mutmut_44, 
    'analyze_pgn__mutmut_45': analyze_pgn__mutmut_45, 
    'analyze_pgn__mutmut_46': analyze_pgn__mutmut_46, 
    'analyze_pgn__mutmut_47': analyze_pgn__mutmut_47, 
    'analyze_pgn__mutmut_48': analyze_pgn__mutmut_48, 
    'analyze_pgn__mutmut_49': analyze_pgn__mutmut_49, 
    'analyze_pgn__mutmut_50': analyze_pgn__mutmut_50, 
    'analyze_pgn__mutmut_51': analyze_pgn__mutmut_51, 
    'analyze_pgn__mutmut_52': analyze_pgn__mutmut_52, 
    'analyze_pgn__mutmut_53': analyze_pgn__mutmut_53, 
    'analyze_pgn__mutmut_54': analyze_pgn__mutmut_54, 
    'analyze_pgn__mutmut_55': analyze_pgn__mutmut_55, 
    'analyze_pgn__mutmut_56': analyze_pgn__mutmut_56, 
    'analyze_pgn__mutmut_57': analyze_pgn__mutmut_57, 
    'analyze_pgn__mutmut_58': analyze_pgn__mutmut_58, 
    'analyze_pgn__mutmut_59': analyze_pgn__mutmut_59, 
    'analyze_pgn__mutmut_60': analyze_pgn__mutmut_60, 
    'analyze_pgn__mutmut_61': analyze_pgn__mutmut_61, 
    'analyze_pgn__mutmut_62': analyze_pgn__mutmut_62, 
    'analyze_pgn__mutmut_63': analyze_pgn__mutmut_63, 
    'analyze_pgn__mutmut_64': analyze_pgn__mutmut_64, 
    'analyze_pgn__mutmut_65': analyze_pgn__mutmut_65, 
    'analyze_pgn__mutmut_66': analyze_pgn__mutmut_66, 
    'analyze_pgn__mutmut_67': analyze_pgn__mutmut_67, 
    'analyze_pgn__mutmut_68': analyze_pgn__mutmut_68, 
    'analyze_pgn__mutmut_69': analyze_pgn__mutmut_69, 
    'analyze_pgn__mutmut_70': analyze_pgn__mutmut_70, 
    'analyze_pgn__mutmut_71': analyze_pgn__mutmut_71, 
    'analyze_pgn__mutmut_72': analyze_pgn__mutmut_72, 
    'analyze_pgn__mutmut_73': analyze_pgn__mutmut_73, 
    'analyze_pgn__mutmut_74': analyze_pgn__mutmut_74, 
    'analyze_pgn__mutmut_75': analyze_pgn__mutmut_75, 
    'analyze_pgn__mutmut_76': analyze_pgn__mutmut_76, 
    'analyze_pgn__mutmut_77': analyze_pgn__mutmut_77, 
    'analyze_pgn__mutmut_78': analyze_pgn__mutmut_78, 
    'analyze_pgn__mutmut_79': analyze_pgn__mutmut_79, 
    'analyze_pgn__mutmut_80': analyze_pgn__mutmut_80
}

def analyze_pgn(*args, **kwargs):
    return _mutmut_trampoline(analyze_pgn__mutmut_orig, analyze_pgn__mutmut_mutants, *args, **kwargs) 

analyze_pgn.__signature__ = _mutmut_signature(analyze_pgn__mutmut_orig)
analyze_pgn__mutmut_orig.__name__ = 'analyze_pgn'




# Alias conservé pour compatibilité avec la spécification historique.
analyze_blunders = analyze_pgn
