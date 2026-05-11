#!/usr/bin/env bash
set -euo pipefail

SIM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRONLY_DIR="$(cd "${SIM_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DRONLY_DIR}/.." && pwd)"

RH_PORT="${RH_PORT:-5000}"
SIM_NODES="${SIM_NODES:-4}"
SIM_DATA_DIR="${SIM_DATA_DIR:-${SIM_DIR}/data}"

if lsof -nP -iTCP:"${RH_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${RH_PORT} is already in use."
  echo "Stop the existing RotorHazard server first, or point the other scripts at another server with RH_SOCKET_URL."
  lsof -nP -iTCP:"${RH_PORT}" -sTCP:LISTEN || true
  exit 1
fi

if [[ ! -f "${REPO_ROOT}/venv/bin/activate" ]]; then
  echo "Missing venv. Create it from the repo root first:"
  echo "  python -m venv venv"
  echo "  source venv/bin/activate"
  echo "  pip install -r src/server/requirements.txt"
  exit 1
fi

mkdir -p "${SIM_DATA_DIR}"

if [[ ! -f "${SIM_DATA_DIR}/config.json" ]]; then
  cat > "${SIM_DATA_DIR}/config.json" <<JSON
{"GENERAL":{"HTTP_PORT":${RH_PORT},"CORS_ALLOWED_HOSTS":"*","SERIAL_PORTS":[],"MOCK_NODES":0}}
JSON
fi

echo "Starting RotorHazard with ${SIM_NODES} mock nodes on port ${RH_PORT}."
echo "Simulation data directory: ${SIM_DATA_DIR}"
echo "Leave this terminal open. Press Ctrl-C to stop the server."

cd "${REPO_ROOT}/src/server"
source "${REPO_ROOT}/venv/bin/activate"
exec python server.py --data "${SIM_DATA_DIR}" --mock-nodes "${SIM_NODES}"
