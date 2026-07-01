# Backend Chess Improver — image Docker avec Stockfish natif (EPIC 2).
# Render build cette image à chaque déploiement : Stockfish est donc installé
# automatiquement, sans action manuelle.

FROM python:3.11-slim

# Stockfish natif → binaire installé dans /usr/games/stockfish (Debian).
RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/*

ENV STOCKFISH_PATH=/usr/games/stockfish \
    ENGINE_DEPTH=14 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render fournit $PORT ; défaut 8000 en local.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
