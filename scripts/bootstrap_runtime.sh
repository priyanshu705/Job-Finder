#!/usr/bin/env bash
set -euo pipefail

python scripts/check_python_version.py
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install --with-deps chromium

