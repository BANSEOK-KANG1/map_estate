#!/usr/bin/env bash
# Flutter web → backend/static/web 동기화 (배포용)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/flutter_sdk/bin:${PATH}"

cd "$ROOT/app"
flutter build web --release

rm -rf "$ROOT/backend/static/web"
mkdir -p "$ROOT/backend/static"
cp -R "$ROOT/app/build/web" "$ROOT/backend/static/web"
echo "Synced → backend/static/web"
