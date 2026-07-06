# Backend Chess Improver — image Docker avec Stockfish natif (EPIC 2).
# Render build cette image à chaque déploiement : Stockfish est donc installé
# automatiquement, sans action manuelle.

FROM python:3.11-slim

# Stockfish natif → binaire installé dans /usr/games/stockfish (Debian).
RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish curl \
    && rm -rf /var/lib/apt/lists/*

ENV STOCKFISH_PATH=/usr/games/stockfish \
    ENGINE_DEPTH=14 \
    PYTHONUNBUFFERED=1

# DATABASE_URL (CockroachDB Cloud, EPIC 39) utilise sslmode=verify-full : le
# certificat racine du cluster doit être présent, sinon psycopg échoue avec
# « root certificate file ... does not exist ». Couplé à ce cluster précis
# (identifiant dans l'URL) — à mettre à jour si le cluster est recréé.
RUN mkdir -p /root/.postgresql \
    && curl --create-dirs -o /root/.postgresql/root.crt \
    'https://cockroachlabs.cloud/clusters/206ab806-09a1-4320-8a47-2080e53e9b40/cert'

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render fournit $PORT ; défaut 8000 en local.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
