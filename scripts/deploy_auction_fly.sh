#!/usr/bin/env bash
# Auction Insight → Fly.io 배포
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AI="$ROOT/auction_insight"
APP="${FLY_APP:-auction-insight-app}"
cd "$AI"

if ! flyctl auth whoami >/dev/null 2>&1; then
  echo "Fly 로그인이 필요합니다."
  flyctl auth login
fi

# Flutter web → backend/static/web (same-origin API)
if command -v flutter >/dev/null 2>&1 || [ -x "$HOME/flutter_sdk/bin/flutter" ]; then
  export PATH="${HOME}/flutter_sdk/bin:${PATH}"
  API_BASE_URL="" bash "$AI/backend/scripts/sync_web.sh"
else
  echo "flutter 없음 — 기존 backend/static/web 사용"
  test -d "$AI/backend/static/web" || {
    echo "backend/static/web 이 없습니다. flutter build web 후 다시 실행하세요."
    exit 1
  }
fi

if ! flyctl status -a "$APP" >/dev/null 2>&1; then
  flyctl apps create "$APP" --org personal || true
  flyctl volumes create auction_data --region nrt --size 1 -a "$APP" || true
fi

# Secrets from local .env (values never echoed)
ENV_FILE="$AI/backend/.env"
if [ -f "$ENV_FILE" ]; then
  get_kv() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-; }
  ONBID_SERVICE_KEY="$(get_kv ONBID_SERVICE_KEY)"
  MOLIT_SERVICE_KEY="$(get_kv MOLIT_SERVICE_KEY)"
  KAKAO_REST_KEY="$(get_kv KAKAO_REST_KEY)"
  ARGS=()
  [ -n "${ONBID_SERVICE_KEY:-}" ] && ARGS+=(ONBID_SERVICE_KEY="$ONBID_SERVICE_KEY")
  [ -n "${MOLIT_SERVICE_KEY:-}" ] && ARGS+=(MOLIT_SERVICE_KEY="$MOLIT_SERVICE_KEY")
  [ -n "${KAKAO_REST_KEY:-}" ] && ARGS+=(KAKAO_REST_KEY="$KAKAO_REST_KEY")
  if [ "${#ARGS[@]}" -gt 0 ]; then
    flyctl secrets set "${ARGS[@]}" -a "$APP"
  fi
fi

flyctl deploy --config fly.toml --remote-only -a "$APP"
echo ""
echo "URL: https://${APP}.fly.dev"
echo "배포 직후 DB는 비어 있을 수 있습니다. 설정에서 온비드 수집을 실행하거나:"
echo "  curl -X POST https://${APP}.fly.dev/api/ingest/onbid -H 'Content-Type: application/json' -d '{\"max_pages\":5,\"page_size\":100,\"clear_onbid\":false,\"enrich\":false}'"
