#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"

VERCEL_SCOPE_VALUE="${VERCEL_SCOPE:-}"
VERCEL_TOKEN_VALUE="${VERCEL_TOKEN:-}"
DEPLOY_MODE="preview"

for arg in "$@"; do
  case "$arg" in
    --prod)
      DEPLOY_MODE="production"
      ;;
    --preview)
      DEPLOY_MODE="preview"
      ;;
    *)
      echo "지원하지 않는 옵션: $arg" >&2
      echo "사용법: ./scripts/vercel_deploy.sh [--prod|--preview]" >&2
      exit 1
      ;;
  esac
done

if ! command -v vercel >/dev/null 2>&1; then
  echo "vercel CLI를 찾을 수 없습니다. 먼저 'npm i -g vercel' 또는 'pnpm add -g vercel'로 설치하세요." >&2
  exit 1
fi

require_linked_project() {
  local dir="$1"
  local label="$2"

  if [[ ! -f "$dir/.vercel/project.json" ]]; then
    echo "[$label] Vercel 프로젝트가 아직 링크되지 않았습니다." >&2
    echo "먼저 ./scripts/vercel_link.sh 를 실행하세요." >&2
    exit 1
  fi
}

deploy_project() {
  local dir="$1"
  local label="$2"
  local -a extra_args=()
  local -a common_args=()
  local frontend_backend_base_url="${BACKEND_API_BASE_URL:-${BACKEND_DEPLOYMENT_URL:-}}"
  local url

  common_args+=("--yes")

  if [[ "$DEPLOY_MODE" == "production" ]]; then
    common_args+=("--prod")
  fi

  if [[ -n "$VERCEL_SCOPE_VALUE" ]]; then
    common_args+=("--scope" "$VERCEL_SCOPE_VALUE")
  fi

  if [[ -n "$VERCEL_TOKEN_VALUE" ]]; then
    common_args+=("--token" "$VERCEL_TOKEN_VALUE")
  fi

  if [[ "$label" == "backend" && -n "${OPENAI_API_KEY:-}" ]]; then
    extra_args+=("--env" "OPENAI_API_KEY=$OPENAI_API_KEY")
  fi

  if [[ "$label" == "frontend" && -n "$frontend_backend_base_url" ]]; then
    extra_args+=("--env" "BACKEND_API_BASE_URL=$frontend_backend_base_url")
  fi

  echo "[$label] ${DEPLOY_MODE} 배포 중..."
  if [[ ${#extra_args[@]} -gt 0 ]]; then
    url="$(vercel --cwd "$dir" "${common_args[@]}" "${extra_args[@]}")"
  else
    url="$(vercel --cwd "$dir" "${common_args[@]}")"
  fi
  echo "[$label] 배포 완료: $url"
  echo

  if [[ "$label" == "backend" ]]; then
    BACKEND_DEPLOYMENT_URL="$url"
  elif [[ "$label" == "frontend" ]]; then
    FRONTEND_DEPLOYMENT_URL="$url"
  fi
}

require_linked_project "$FRONTEND_DIR" "frontend"
require_linked_project "$BACKEND_DIR" "backend"

deploy_project "$BACKEND_DIR" "backend"
deploy_project "$FRONTEND_DIR" "frontend"

echo "배포 요약"
echo "- backend:  ${BACKEND_DEPLOYMENT_URL:-unknown}"
echo "- frontend: ${FRONTEND_DEPLOYMENT_URL:-unknown}"
echo
echo "배포된 프론트 기본 API 경로는 /api 입니다."
