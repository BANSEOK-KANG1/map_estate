#!/usr/bin/env bash
# 온비드 실데이터 수집 + (가능 시) 시세/상권 enrich
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate 2>/dev/null || true

API="${API_BASE_URL:-http://127.0.0.1:8001}"
PAGES="${MAX_PAGES:-5}"

echo "== health =="
curl -s "$API/api/health" | python3 -m json.tool

echo
echo "== ingest onbid (clear_demo=true, pages=$PAGES) =="
curl -s -X POST "$API/api/ingest/onbid" \
  -H 'Content-Type: application/json' \
  -d "{\"max_pages\": $PAGES, \"page_size\": 20, \"clear_demo\": true, \"enrich\": true, \"enrich_limit\": 40}" \
  | python3 -m json.tool

echo
echo "== search sample =="
curl -s -X POST "$API/api/search" \
  -H 'Content-Type: application/json' \
  -d '{"sources":["onbid"],"limit":5}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('total', d['total']);
[print('-', i['source_label'], i['title'][:40], i.get('address','')[:40]) for i in d['items'][:5]]"
