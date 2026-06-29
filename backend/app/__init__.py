"""Chess Improver – package applicatif backend.

Architecture en couches :
  - ``app.domain``      : logique métier PURE (zéro dépendance framework).
  - ``app.infrastructure``: passerelles I/O (clients HTTP, persistance).
  - ``app.main``        : assemblage FastAPI (routes de synchronisation).
"""

__version__ = "1.0.0"
