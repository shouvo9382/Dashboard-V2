#!/bin/bash
# macOS launcher — double-click to run.
cd "$(dirname "$0")" || exit 1

echo "================================================"
echo "  National Athlete Performance Dashboard"
echo "================================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[X] Python 3 not found. Install it from https://python.org, then retry."
  read -r -p "Press Enter to close..."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/3] First-time setup: creating environment..."
  python3 -m venv .venv || { echo "[X] venv failed"; read -r; exit 1; }
fi

if [ ! -f ".venv/.installed" ]; then
  echo "[2/3] First-time setup: installing packages (needs internet, ~2 min)..."
  .venv/bin/python -m pip install --upgrade pip --quiet
  .venv/bin/python -m pip install -r requirements.txt || {
    echo "[X] Install failed. Check your internet connection."; read -r; exit 1; }
  echo done > .venv/.installed
else
  echo "[1-2/3] Setup already done - skipping."
fi

echo "[3/3] Starting the dashboard..."
echo
echo "  KEEP THIS TERMINAL WINDOW OPEN during the demo."
echo "  Closing it shuts the dashboard down."
echo
.venv/bin/python -m streamlit run app.py --server.port 8501
