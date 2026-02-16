#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Installation complete."
echo "Run web app: source .venv/bin/activate && python app.py"
echo "Run CLI: source .venv/bin/activate && python cli.py /path/to/file.pdf"
