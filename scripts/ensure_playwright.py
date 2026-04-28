"""
Render-safe Playwright browser verifier.

The Python package install does not include browser binaries. This script checks
the exact Chromium path Playwright will use at runtime and installs Chromium if
that binary is missing.
"""

from __future__ import annotations

import os
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify or install Playwright Chromium.")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only verify the expected Chromium path; do not download the browser.",
    )
    args = parser.parse_args()

    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
    os.environ.pop("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD", None)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        chromium_path = Path(playwright.chromium.executable_path)

    if chromium_path.exists():
        print(f"[playwright] Chromium found: {chromium_path}")
        return 0

    print(f"[playwright] Chromium missing: {chromium_path}")
    if args.check_only:
        return 1

    print("[playwright] Installing Chromium browser...")

    subprocess.check_call(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": os.environ["PLAYWRIGHT_BROWSERS_PATH"]},
    )

    if chromium_path.exists():
        print(f"[playwright] Chromium installed: {chromium_path}")
        return 0

    print(f"[playwright] Chromium still missing after install: {chromium_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
