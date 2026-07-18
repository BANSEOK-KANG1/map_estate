#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/app"
flutter build web --dart-define=API_BASE_URL="${API_BASE_URL:-}"
mkdir -p "$ROOT/backend/static"
rm -rf "$ROOT/backend/static/web"
cp -R "$ROOT/app/build/web" "$ROOT/backend/static/web"
echo "Synced web build → backend/static/web"
