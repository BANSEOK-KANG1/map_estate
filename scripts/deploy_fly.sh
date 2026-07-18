#!/usr/bin/env bash
# 상시 배포 (Fly.io)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! flyctl auth whoami >/dev/null 2>&1; then
  echo "Fly 로그인이 필요합니다. 브라우저에서 승인하세요."
  flyctl auth login
fi

# sync web if flutter available
if command -v flutter >/dev/null 2>&1 || [ -x "$HOME/flutter_sdk/bin/flutter" ]; then
  export PATH="${HOME}/flutter_sdk/bin:${PATH}"
  bash backend/scripts/sync_web.sh || true
fi

# Create app + volume once
if ! flyctl status -a map-estate-app >/dev/null 2>&1; then
  flyctl apps create map-estate-app --org personal || true
  flyctl volumes create estate_data --region nrt --size 1 -a map-estate-app || true
fi

# Secrets from local .env (never printed)
if [ -f backend/.env ]; then
  # shellcheck disable=SC1091
  set -a
  # Only export keys we need
  MOLIT_SERVICE_KEY="$(grep '^MOLIT_SERVICE_KEY=' backend/.env | cut -d= -f2-)"
  KAKAO_REST_KEY="$(grep '^KAKAO_REST_KEY=' backend/.env | cut -d= -f2- || true)"
  set +a
  ARGS=(MOLIT_SERVICE_KEY="$MOLIT_SERVICE_KEY")
  if [ -n "${KAKAO_REST_KEY:-}" ]; then
    ARGS+=(KAKAO_REST_KEY="$KAKAO_REST_KEY")
  fi
  flyctl secrets set "${ARGS[@]}" -a map-estate-app
fi

flyctl deploy --config fly.toml --dockerfile backend/Dockerfile --remote-only -a map-estate-app
echo "URL: https://map-estate-app.fly.dev"
