#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/app"

BUILD_ID="$(python3 - <<'PY'
from pathlib import Path
import re
text = Path("pubspec.yaml").read_text()
m = re.search(r"^version:\s*([^\s]+)", text, re.M)
print((m.group(1) if m else "dev").replace("+", "."))
PY
)-$(date +%s)"

flutter build web --dart-define=API_BASE_URL="${API_BASE_URL:-}"

# Inject cache-buster into index + bootstrap so browsers don't keep old main.dart.js
INDEX="$ROOT/app/build/web/index.html"
BOOT="$ROOT/app/build/web/flutter_bootstrap.js"
if [[ -f "$INDEX" ]]; then
  python3 - <<PY
from pathlib import Path
build_id = "${BUILD_ID}"
index = Path("${INDEX}")
text = index.read_text()
text = text.replace("BUILD_ID_PLACEHOLDER", build_id)
index.write_text(text)
boot = Path("${BOOT}")
if boot.exists():
    b = boot.read_text()
    b = b.replace('"main.dart.js"', f'"main.dart.js?v={build_id}"')
    b = b.replace("'main.dart.js'", f"'main.dart.js?v={build_id}'")
    boot.write_text(b)
print(f"cache-busted build_id={build_id}")
PY
fi

mkdir -p "$ROOT/backend/static"
rm -rf "$ROOT/backend/static/web"
cp -R "$ROOT/app/build/web" "$ROOT/backend/static/web"
echo "Synced web build → backend/static/web"
