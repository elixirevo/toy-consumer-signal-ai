#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"

FRONTEND_PROJECT="${FRONTEND_VERCEL_PROJECT:-}"
BACKEND_PROJECT="${BACKEND_VERCEL_PROJECT:-}"
VERCEL_SCOPE_VALUE="${VERCEL_SCOPE:-}"
VERCEL_TOKEN_VALUE="${VERCEL_TOKEN:-}"

if ! command -v vercel >/dev/null 2>&1; then
  echo "vercel CLI를 찾을 수 없습니다. 먼저 'npm i -g vercel' 또는 'pnpm add -g vercel'로 설치하세요." >&2
  exit 1
fi

run_vercel() {
  local -a cmd=("vercel" "$@")

  if [[ -n "$VERCEL_SCOPE_VALUE" ]]; then
    cmd+=("--scope" "$VERCEL_SCOPE_VALUE")
  fi

  if [[ -n "$VERCEL_TOKEN_VALUE" ]]; then
    cmd+=("--token" "$VERCEL_TOKEN_VALUE")
  fi

  "${cmd[@]}"
}

link_project() {
  local dir="$1"
  local project_name="$2"
  local label="$3"

  echo "[$label] Vercel 프로젝트 링크 중..."

  if [[ -n "$project_name" ]]; then
    run_vercel link --cwd "$dir" --yes --project "$project_name"
  else
    echo "[$label] FRONTEND_VERCEL_PROJECT / BACKEND_VERCEL_PROJECT 값이 없어서 interactive link로 진행합니다."
    run_vercel link --cwd "$dir"
  fi

  echo "[$label] 링크 완료"
  echo
}

link_project "$FRONTEND_DIR" "$FRONTEND_PROJECT" "frontend"
link_project "$BACKEND_DIR" "$BACKEND_PROJECT" "backend"

echo "frontend와 backend 디렉터리를 각각 Vercel 프로젝트에 연결했습니다."
