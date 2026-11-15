#!/usr/bin/env bash
# docs/codelab/preview.sh: preview the codelab locally in your browser.
# Uses either QNX's claat tool (Google Codelabs format) or the site generator.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

PORT="${1:-8080}"

if command -v claat >/dev/null 2>&1; then
    echo "Using claat to render QNX codelab format..."
    TMP_OUT="$(mktemp -d /tmp/qnx-codelab-XXXXXX)"
    claat export -f html -o "$TMP_OUT" "$HERE/qnx-codelabs-format/markdown/port-cmake-library-qnx/port-cmake-library-qnx.md"
    echo "Serving preview at http://localhost:$PORT/port-cmake-library-qnx/index.html (Ctrl+C to stop)..."
    python3 -m http.server "$PORT" --directory "$TMP_OUT"
else
    echo "claat not found; using repository site generator..."
    python3 "$ROOT/site/build.py"
    echo "Serving preview at http://localhost:$PORT/codelab-port-a-library.html (Ctrl+C to stop)..."
    python3 -m http.server "$PORT" --directory "$ROOT/site/_out"
fi
