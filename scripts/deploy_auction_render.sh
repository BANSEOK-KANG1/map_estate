#!/usr/bin/env bash
# Auction Insight → GitHub push + Render 안내 (기존 map_estate와 동일 방식)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AI="$ROOT/auction_insight"
cd "$ROOT"

# Flutter web (same-origin)
if command -v flutter >/dev/null 2>&1 || [ -x "$HOME/flutter_sdk/bin/flutter" ]; then
  export PATH="${HOME}/flutter_sdk/bin:${PATH}"
  API_BASE_URL="" bash "$AI/backend/scripts/sync_web.sh"
fi

echo ""
echo "=== Render 배포 (예전에 map_estate에 쓰신 방식) ==="
echo "1) GitHub에 auction_insight 변경사항 push"
echo "2) https://dashboard.render.com → New → Blueprint"
echo "   - Repo: map_estate"
echo "   - Blueprint: auction_insight/render.yaml"
echo "   - 또는 Root Directory를 auction_insight 로 지정"
echo "3) Environment에 키 입력:"
echo "   ONBID_SERVICE_KEY / MOLIT_SERVICE_KEY / KAKAO_REST_KEY"
echo "4) Deploy 후 URL 예: https://auction-insight.onrender.com"
echo ""
echo "무료 플랜은 유휴 시 잠듭니다(PC 켤 필요 없음). 첫 접속 수십 초 걸릴 수 있음."
echo "무료는 디스크가 비영속이라, 깨운 뒤 설정에서 '온비드 수집'을 한 번 돌리면 됩니다."
echo ""

if command -v open >/dev/null 2>&1; then
  open "https://dashboard.render.com/select-repo?type=blueprint" 2>/dev/null || open "https://dashboard.render.com" || true
fi

# Optional: try Railway if user prefers CLI
if command -v railway >/dev/null 2>&1; then
  echo "Railway CLI도 로그인되어 있습니다. Railway로 올리려면:"
  echo "  cd auction_insight && railway init && railway up --dockerfile backend/Dockerfile"
fi
