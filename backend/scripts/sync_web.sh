#!/usr/bin/env bash
# Flutter web → backend/static/web 동기화 (배포용)
set -euo pipefail
BACKEND="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$BACKEND/.." && pwd)"
export PATH="${HOME}/flutter_sdk/bin:${PATH}"

cd "$ROOT/app"
flutter build web --release

rm -rf "$BACKEND/static/web"
mkdir -p "$BACKEND/static"
cp -R "$ROOT/app/build/web" "$BACKEND/static/web"
echo "Synced → backend/static/web"
