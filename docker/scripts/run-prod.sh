#!/usr/bin/env sh
# Run production image without docker-compose.
# Usage: ./run-prod.sh [DATA_DIR]
#   DATA_DIR defaults to ./data (relative to current directory).
#   Example: ./run-prod.sh /opt/rotorhazard/data
#
# USB/serial (timing Arduino): Works on Linux/WSL/Windows. On macOS, Docker Desktop
# cannot pass host USB devices into the container; use a native install for timing hardware.

set -e
IMAGE="${IMAGE:-racefpv/rotorhazard:latest}"
DATA_DIR="${1:-./data}"

docker run -d \
  --name rotorhazard-server \
  --restart unless-stopped \
  -p 5000:5000 \
  -v "${DATA_DIR}:/app/data" \
  -e RH_DATA_DIR=/app/data \
  --privileged \
  "$IMAGE"

echo "RotorHazard running at http://localhost:5000 (data: ${DATA_DIR})"
