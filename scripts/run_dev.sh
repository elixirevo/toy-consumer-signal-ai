#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"

BACKEND_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"

if [[ ! -x "$BACKEND_UVICORN" ]]; then
  echo "backend/.venv/bin/uvicorn 을 찾을 수 없습니다." >&2
  echo "먼저 backend 가상환경과 의존성을 준비하세요." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 명령을 찾을 수 없습니다." >&2
  exit 1
fi

cleanup() {
  local exit_code=$?

  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi

  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi

  wait >/dev/null 2>&1 || true
  exit "$exit_code"
}

trap cleanup INT TERM EXIT

echo "Backend:  http://$BACKEND_HOST:$BACKEND_PORT"
echo "Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
echo

(
  cd "$BACKEND_DIR"
  exec "$BACKEND_UVICORN" main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

(
  cd "$FRONTEND_DIR"
  exec python3 -m http.server "$FRONTEND_PORT" --bind "$FRONTEND_HOST"
) &
FRONTEND_PID=$!

echo "두 서버를 시작했습니다. 종료하려면 Ctrl+C 를 누르세요."
echo

while true; do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    wait "$BACKEND_PID" || true
    break
  fi

  if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    wait "$FRONTEND_PID" || true
    break
  fi

  sleep 1
done
