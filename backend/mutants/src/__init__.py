
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


"""Logique métier pure du domaine Chess Improver.

Ce sous-paquet ne doit dépendre d'aucun framework : ni FastAPI, ni client HTTP.
Il expose :
  - :mod:`models`          : contrats Pydantic / dataclasses.
  - :mod:`elo_calculator`  : estimation d'Elo de performance (CAPS simplifié).
  - :mod:`srs_engine`      : répétition espacée SuperMemo-2.
  - :mod:`analyzer`        : moteur de règles géométriques (gaffes, fourchettes, zeitnot).
"""
