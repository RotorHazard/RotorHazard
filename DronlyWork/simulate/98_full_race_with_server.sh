#!/usr/bin/env bash
set -euo pipefail

SIM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RH_PORT="${RH_PORT:-5000}"
RH_SOCKET_URL="${RH_SOCKET_URL:-http://localhost:${RH_PORT}}"
SERVER_LOG="${SERVER_LOG:-${SIM_DIR}/mock_server.log}"

export RH_SOCKET_URL

if lsof -nP -iTCP:"${RH_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Using existing RotorHazard server on port ${RH_PORT}."
  exec "${SIM_DIR}/99_full_race_demo.sh"
fi

echo "Starting temporary RotorHazard mock server on port ${RH_PORT}."
"${SIM_DIR}/00_start_mock_server.sh" > "${SERVER_LOG}" 2>&1 &
server_pid=$!

cleanup() {
  if kill -0 "${server_pid}" >/dev/null 2>&1; then
    echo "Stopping temporary RotorHazard mock server."
    kill "${server_pid}" >/dev/null 2>&1 || true
    wait "${server_pid}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

for _ in $(seq 1 90); do
  if curl -fsS "${RH_SOCKET_URL}/" >/dev/null 2>&1; then
    break
  fi

  if ! kill -0 "${server_pid}" >/dev/null 2>&1; then
    echo "RotorHazard server exited while starting. Log:"
    cat "${SERVER_LOG}" || true
    exit 1
  fi

  sleep 1
done

if ! curl -fsS "${RH_SOCKET_URL}/" >/dev/null 2>&1; then
  echo "RotorHazard did not become reachable at ${RH_SOCKET_URL}."
  echo "Log:"
  cat "${SERVER_LOG}" || true
  exit 1
fi

echo "RotorHazard is reachable at ${RH_SOCKET_URL}."
"${SIM_DIR}/99_full_race_demo.sh"
