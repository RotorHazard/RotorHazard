# RotorHazard Server Dockerfile - non-Pi (x64/amd64)
# Python 3.10+ is required (MIN_PYTHON_MAJOR_VERSION = 3, MIN_PYTHON_MINOR_VERSION = 10)
#
# Build context must be the repo root (parent of docker/), e.g.:
#   docker build -f docker/Dockerfile .
# Or use docker-compose from docker/: docker-compose build
#
# Stages:
#   base    - Common app layout and system deps (no Python deps). Used by Dockerfile.pi.
#   default - x64 image with reqsNonPi.txt (default target).
#
# For Pi image use: Dockerfile.pi (FROM racefpv/rotorhazard:base)
FROM python:3.11-slim AS base

WORKDIR /app

# Common system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application (Python deps installed by each variant)
COPY src/server/ /app/src/server/
COPY src/interface/ /app/src/interface/
COPY firmware/ /app/firmware/

# -----------------------------------------------------------------------------
# Default (x64) image: non-Pi requirements
# -----------------------------------------------------------------------------
FROM base AS default

COPY src/server/reqsNonPi.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app/src/server
RUN mkdir -p /app/data
VOLUME /app/data
EXPOSE 5000
ENV RH_DATA_DIR=/app/data
CMD ["python", "server.py", "--data", "/app/data"]
