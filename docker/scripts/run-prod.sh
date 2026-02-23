#!/usr/bin/env sh
# Run production image without docker-compose.
# Usage: ./run-prod.sh [DATA_DIR]
#   DATA_DIR defaults to ./data (relative to current directory).
#   Example: ./run-prod.sh /opt/rotorhazard/data

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
