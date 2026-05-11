#!/usr/bin/env bash
set -euo pipefail

SIM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRONLY_DIR="$(cd "${SIM_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DRONLY_DIR}/.." && pwd)"

export RH_SOCKET_URL="${RH_SOCKET_URL:-http://localhost:5000}"
export SIM_NODES="${SIM_NODES:-4}"

ensure_node_modules() {
  if [[ ! -d "${DRONLY_DIR}/node_modules/socket.io-client" ]]; then
    echo "Missing DronlyWork/node_modules. Run this first:"
    echo "  cd \"${DRONLY_DIR}\" && npm install"
    exit 1
  fi
}

run_sim() {
  ensure_node_modules
  node "${SIM_DIR}/rh_sim_client.mjs" "$@"
}
