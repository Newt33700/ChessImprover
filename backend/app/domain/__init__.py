"""Logique métier pure du domaine Chess Improver.

Ce sous-paquet ne doit dépendre d'aucun framework : ni FastAPI, ni client HTTP.
Il expose :
  - :mod:`models`          : contrats Pydantic / dataclasses.
  - :mod:`elo_calculator`  : estimation d'Elo de performance (CAPS simplifié).
  - :mod:`srs_engine`      : répétition espacée SuperMemo-2.
  - :mod:`analyzer`        : moteur de règles géométriques (gaffes, fourchettes, zeitnot).
"""
