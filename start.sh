#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_banner() {
  echo ""
  echo "  ╔════════════════════════════════════════╗"
  echo "  ║    AI Connector Marketplace v1.0.0     ║"
  echo "  ╚════════════════════════════════════════╝"
  echo ""
}

check_python() {
  if ! command -v python3 &>/dev/null; then
    echo "❌  Python 3 is required. Install from https://python.org"
    exit 1
  fi
  echo "✅  Python: $(python3 --version)"
}

setup_venv() {
  if [ ! -d ".venv" ]; then
    echo "📦  Creating virtual environment…"
    python3 -m venv .venv
  fi

  # Activate
  # shellcheck disable=SC1091
  source .venv/bin/activate

  echo "📦  Installing backend dependencies…"
  pip install --quiet -r backend/requirements.txt
  echo "✅  Dependencies installed"
}

start_backend() {
  local port="${PORT:-8765}"
  echo ""
  echo "🚀  Starting backend on http://localhost:${port}"
  echo "📄  API docs available at http://localhost:${port}/docs"
  echo "    (override with: PORT=xxxx ./start.sh)"
  echo ""
  uvicorn backend.main:app --host 0.0.0.0 --port "${port}" --reload --log-level info
}

print_banner
check_python
setup_venv
start_backend
