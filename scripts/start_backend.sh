#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"
python scripts/check_python_version.py
exec gunicorn app:app

