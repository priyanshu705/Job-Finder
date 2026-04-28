"""
setup.py
--------
Project setup verifier.
Run this ONCE after cloning the repo to:
  1. Check Python version
  2. Check all required packages are installed
  3. Check .env file exists
  4. Initialize the SQLite database
  5. Verify Playwright + spaCy are ready
  6. Print a clear status report

Usage:
    python setup.py
"""

import sys
import os
import importlib
from typing import Callable, Any

# Resolve project root and add 'src' to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

# ── ANSI colors ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

PASS = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"
WARN = f"{YELLOW}⚠{RESET}"


def check(label: str, fn: Callable[[], Any]) -> bool:
    try:
        result = fn()
        if result is True or result is None:
            print(f"  {PASS}  {label}")
            return True
        elif result is False:
            print(f"  {FAIL}  {label}")
            return False
        else:
            print(f"  {PASS}  {label} — {result}")
            return True
    except Exception as exc:
        print(f"  {FAIL}  {label} — {RED}{exc}{RESET}")
        return False


def main():
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"{BOLD}  AutoApply AI — Setup Verification{RESET}")
    print(f"{BOLD}{'='*50}{RESET}\n")

    failures = 0

    # ── 1. Python version ────────────────────────────────────────────────
    print(f"{BOLD}[1] Python Version{RESET}")
    ok = check(
        f"Python {sys.version.split()[0]}",
        lambda: sys.version_info >= (3, 10)
    )
    if not ok:
        print(f"      {RED}Python 3.10+ required. Found: {sys.version}{RESET}")
        failures += 1

    # ── 2. Required packages ─────────────────────────────────────────────
    print(f"\n{BOLD}[2] Required Packages{RESET}")
    packages = {
        "playwright":      "playwright",
        "beautifulsoup4":  "bs4",
        "scikit-learn":    "sklearn",
        "spacy":           "spacy",
        "pdfplumber":      "pdfplumber",
        "docx2txt":        "docx2txt",
        "gspread":         "gspread",
        "google-auth":     "google.auth",
        "python-dotenv":   "dotenv",
        "flask":           "flask",
    }
    for display_name, import_name in packages.items():
        ok = check(display_name, lambda n=import_name: importlib.import_module(n) is not None)
        if not ok:
            failures += 1

    # ── 3. spaCy model ───────────────────────────────────────────────────
    print(f"\n{BOLD}[3] spaCy Language Model{RESET}")
    def check_spacy():
        import spacy
        nlp = spacy.load("en_core_web_sm")
        return f"en_core_web_sm v{nlp.meta.get('version','?')}"
    ok = check("en_core_web_sm", check_spacy)
    if not ok:
        print(f"      {YELLOW}Run: python -m spacy download en_core_web_sm{RESET}")
        failures += 1

    # ── 4. Playwright browser ────────────────────────────────────────────
    print(f"\n{BOLD}[4] Playwright Browser{RESET}")
    def check_playwright():
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            version = browser.version
            browser.close()
        return f"Chromium {version}"
    ok = check("Chromium browser", check_playwright)
    if not ok:
        print(f"      {YELLOW}Run: playwright install chromium{RESET}")
        failures += 1

    # ── 5. .env file ─────────────────────────────────────────────────────
    print(f"\n{BOLD}[5] Environment Configuration{RESET}")
    def check_env():
        if not os.path.exists(".env"):
            raise FileNotFoundError(".env file not found")
        from dotenv import load_dotenv
        load_dotenv()
        return True
    ok = check(".env file", check_env)
    if not ok:
        print(f"      {YELLOW}Copy .env.example → .env and fill in your values{RESET}")
        failures += 1

    # ── 6. Key env variables ─────────────────────────────────────────────
    print(f"\n{BOLD}[6] Environment Variables{RESET}")
    from dotenv import load_dotenv
    load_dotenv()

    env_vars = {
        "RESUME_PATH":          "Path to your resume PDF",
        "INTERNSHALA_EMAIL":    "Internshala login email",
        "INTERNSHALA_PASSWORD": "Internshala password",
    }
    env_optional = {
        "GOOGLE_SHEET_ID":      "Google Sheets (optional for MVP)",
        "TELEGRAM_TOKEN":       "Telegram alerts (optional)",
    }
    for var, desc in env_vars.items():
        val = os.getenv(var, "")
        ok  = check(f"{var}", lambda v=val: bool(v and v != f"your_{var.lower()}_here"))
        if not ok:
            print(f"      {YELLOW}→ {desc}{RESET}")
            failures += 1

    for var, desc in env_optional.items():
        val = os.getenv(var, "")
        if val:
            print(f"  {PASS}  {var} (configured)")
        else:
            print(f"  {WARN}  {var} — {YELLOW}not set (optional){RESET}")

    # ── 7. Resume file ───────────────────────────────────────────────────
    print(f"\n{BOLD}[7] Resume File{RESET}")
    resume_path = os.getenv("RESUME_PATH", "./resumes/resume.pdf")
    ok = check(f"Resume at {resume_path}", lambda: os.path.exists(resume_path))
    if not ok:
        print(f"      {YELLOW}Place your resume PDF at: {resume_path}{RESET}")
        failures += 1

    # ── 8. Database init ─────────────────────────────────────────────────
    print(f"\n{BOLD}[8] Database Initialization{RESET}")
    def init_database():
        from finder.shared.database import init_db, get_table_counts
        init_db()
        counts = get_table_counts()
        return f"{len(counts)} tables ready"
    ok = check("SQLite database", init_database)
    if not ok:
        failures += 1

    # ── 9. Logger test ───────────────────────────────────────────────────
    print(f"\n{BOLD}[9] Logger System{RESET}")
    def test_logger():
        from finder.shared.logger import get_logger
        log = get_logger("setup_test")
        log.info("Logger test passed")
        return os.path.exists("logs/setup_test.jsonl")
    ok = check("JSON file logger", test_logger)
    if not ok:
        failures += 1

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*50}{RESET}")
    if failures == 0:
        print(f"{GREEN}{BOLD}  ✓ All checks passed! System ready to build.{RESET}")
        print(f"\n  Next step:")
        print(f"  {BOLD}Say 'build scraper' to build the scraper module.{RESET}")
    else:
        print(f"{RED}{BOLD}  ✗ {failures} check(s) failed. Fix above issues first.{RESET}")
    print(f"{BOLD}{'='*50}{RESET}\n")

    return failures == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
