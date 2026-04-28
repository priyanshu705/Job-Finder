"""
src/finder/cli/dashboard.py
--------------------------
AutoApply AI — Live Terminal Dashboard
"""

import os
import sys
import json
import time
import argparse
import sqlite3
import re
import threading
from datetime import datetime, timezone, date, timedelta

from dotenv import load_dotenv
from finder.shared.config import DB_PATH

load_dotenv()

# ── ANSI Color / Style Codes ──────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

# Foreground colors
BLACK   = "\033[30m"
RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
BLUE    = "\033[34m"
MAGENTA = "\033[35m"
CYAN    = "\033[36m"
WHITE   = "\033[37m"

# Bright variants
BGREEN  = "\033[92m"
BYELLOW = "\033[93m"
BBLUE   = "\033[94m"
BMAGENTA= "\033[95m"
BCYAN   = "\033[96m"
BWHITE  = "\033[97m"
BRED    = "\033[91m"

# Background colors
BG_BLACK  = "\033[40m"
BG_BLUE   = "\033[44m"
BG_CYAN   = "\033[46m"
BG_GREEN  = "\033[42m"
BG_RED    = "\033[41m"

# Terminal control
CLEAR_SCREEN   = "\033[2J\033[H"
HIDE_CURSOR    = "\033[?25l"
SHOW_CURSOR    = "\033[?25h"

# ── Terminal Width ────────────────────────────────────────────────────────────
def _tw() -> int:
    try:
        return min(os.get_terminal_size().columns, 100)
    except Exception:
        return 80

# ── Drawing Primitives ────────────────────────────────────────────────────────

def _rule(char: str = "─", color: str = DIM, width: int = 0) -> str:
    w = width or _tw()
    return f"{color}{char * w}{RESET}"

def _box_top(width: int = 0) -> str:
    w = width or _tw()
    return f"{DIM}╭{'─' * (w - 2)}╮{RESET}"

def _box_bot(width: int = 0) -> str:
    w = width or _tw()
    return f"{DIM}╰{'─' * (w - 2)}╯{RESET}"

def _box_row(content: str, width: int = 0) -> str:
    w = width or _tw()
    # Strip ANSI for length calculation
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    visible_len = len(ansi_escape.sub('', content))
    padding = max(w - 2 - visible_len, 0)
    return f"{DIM}│{RESET} {content}{' ' * padding}{DIM}│{RESET}"

def _header(title: str, subtitle: str = "") -> str:
    w = _tw()
    lines = []
    lines.append(f"{BOLD}{BG_BLUE}{' ' * w}{RESET}")
    centered = title.center(w)
    lines.append(f"{BOLD}{BG_BLUE}{BWHITE}{centered}{RESET}")
    if subtitle:
        sub_c = subtitle.center(w)
        lines.append(f"{BG_BLUE}{DIM}{BWHITE}{sub_c}{RESET}")
    lines.append(f"{BOLD}{BG_BLUE}{' ' * w}{RESET}")
    return "\n".join(lines)

def _section(title: str) -> str:
    return f"\n{BOLD}{BCYAN}  ◆ {title}{RESET}  {DIM}{'─' * max(_tw() - len(title) - 6, 4)}{RESET}"

def _kv(label: str, value: str, label_color: str = DIM, val_color: str = BWHITE,
        width: int = 20) -> str:
    return f"  {label_color}{label:<{width}}{RESET} {val_color}{value}{RESET}"

def _bar(value: float, total: float, width: int = 20, color: str = BGREEN) -> str:
    """Render a simple ASCII progress bar."""
    pct  = min(value / max(total, 1), 1.0)
    fill = int(pct * width)
    bar  = f"{'█' * fill}{'░' * (width - fill)}"
    pct_s = f"{pct * 100:.0f}%"
    return f"{color}{bar}{RESET} {BWHITE}{pct_s}{RESET}"

def _status_dot(status: str) -> str:
    dots = {
        "applied":       f"{BGREEN}●{RESET}",
        "pending":       f"{BYELLOW}●{RESET}",
        "skip":          f"{DIM}●{RESET}",
        "failed":        f"{BRED}●{RESET}",
        "uncertain":     f"{BYELLOW}◐{RESET}",
        "external_skip": f"{BLUE}●{RESET}",
        "paused":        f"{MAGENTA}⏸{RESET}",
        "running":       f"{BGREEN}▶{RESET}",
    }
    return dots.get(status, f"{DIM}●{RESET}")

# ── Data Fetchers ─────────────────────────────────────────────────────────────

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _safe_query(sql: str, params: tuple = ()) -> list:
    try:
        with _db() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:
        return []

def _safe_one(sql: str, params: tuple = ()) -> dict:
    rows = _safe_query(sql, params)
    return rows[0] if rows else {}

def fetch_controls() -> dict:
    rows = _safe_query("SELECT key, value FROM user_controls")
    return {r["key"]: r["value"] for r in rows}

def fetch_queue_stats() -> dict:
    rows = _safe_query(
        "SELECT status, COUNT(*) as cnt FROM apply_queue GROUP BY status"
    )
    return {r["status"]: r["cnt"] for r in rows}

def fetch_today_stats() -> dict:
    today = date.today().isoformat()
    row = _safe_one(
        """
        SELECT
            SUM(CASE WHEN status='applied'   THEN 1 ELSE 0 END) as applied,
            SUM(CASE WHEN status='failed'    THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status='uncertain' THEN 1 ELSE 0 END) as uncertain
        FROM apply_queue
        WHERE date(updated_at) = ?
        """,
        (today,),
    )
    return {
        "applied":   int(row.get("applied") or 0),
        "failed":    int(row.get("failed") or 0),
        "uncertain": int(row.get("uncertain") or 0),
    }

def fetch_db_counts() -> dict:
    tables = ["jobs", "apply_queue", "application_outcomes",
              "user_goals", "company_intelligence"]
    counts = {}
    for t in tables:
        row = _safe_one(f"SELECT COUNT(*) as cnt FROM {t}")
        counts[t] = row.get("cnt", 0)
    return counts

def fetch_top_jobs(limit: int = 8) -> list:
    return _safe_query(
        """
        SELECT q.job_url, q.status, q.match_score_at_apply,
               j.title, j.company, j.location
        FROM apply_queue q
        LEFT JOIN jobs j ON j.job_url = q.job_url
        WHERE q.match_score_at_apply IS NOT NULL
        ORDER BY q.match_score_at_apply DESC
        LIMIT ?
        """,
        (limit,),
    )

def fetch_recent_applied(limit: int = 6) -> list:
    return _safe_query(
        """
        SELECT q.status, q.updated_at, q.match_score_at_apply,
               j.title, j.company
        FROM apply_queue q
        LEFT JOIN jobs j ON j.job_url = q.job_url
        WHERE q.status IN ('applied', 'uncertain', 'failed')
        ORDER BY q.updated_at DESC
        LIMIT ?
        """,
        (limit,),
    )

def fetch_last_cycle() -> dict:
    """Read the most recent cycle from logs/cycles.jsonl."""
    # Note: Use LOGS_DIR if available from shared.config
    from finder.shared.config import LOGS_DIR
    path = os.path.join(LOGS_DIR, "cycles.jsonl")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        if lines:
            return json.loads(lines[-1])
    except Exception:
        pass
    return {}

def fetch_outcome_stats() -> dict:
    row = _safe_one(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN outcome='applied'   THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN outcome='failed'    THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN outcome LIKE '%external%' THEN 1 ELSE 0 END) as external
        FROM application_outcomes
        """
    )
    return {
        "total":    int(row.get("total") or 0),
        "success":  int(row.get("success") or 0),
        "failed":   int(row.get("failed") or 0),
        "external": int(row.get("external") or 0),
    }

# ── Dashboard Renderer ────────────────────────────────────────────────────────

def render(refresh_interval: int = 5) -> str:
    now       = datetime.now()
    controls  = fetch_controls()
    q_stats   = fetch_queue_stats()
    today     = fetch_today_stats()
    db_counts = fetch_db_counts()
    top_jobs  = fetch_top_jobs()
    recent    = fetch_recent_applied()
    last_cycle= fetch_last_cycle()
    outcomes  = fetch_outcome_stats()

    is_paused  = controls.get("paused") == "true"
    daily_cap  = int(controls.get("daily_cap", "10"))
    min_match  = controls.get("min_match", "70")
    query      = os.getenv("SEARCH_QUERY", "—").strip()
    user_name  = os.getenv("USER_NAME", "—")

    total_applied = today["applied"] + today["uncertain"]
    remaining_cap = max(daily_cap - total_applied, 0)

    lines = []

    # ── Alerts ─────────────────────────────────────────────────────────────
    manual_req = controls.get("manual_verification_required")
    if manual_req:
        lines.append(f"{BOLD}{BG_RED}{' ' * _tw()}{RESET}")
        lines.append(f"{BOLD}{BG_RED}{BWHITE}{' ⚠️  MANUAL VERIFICATION REQUIRED '.center(_tw())}{RESET}")
        lines.append(f"{BOLD}{BG_RED}{BWHITE}{f' Reason: {manual_req} '.center(_tw())}{RESET}")
        lines.append(f"{BOLD}{BG_RED}{' ' * _tw()}{RESET}\n")

    # ── Header ─────────────────────────────────────────────────────────────
    lines.append(CLEAR_SCREEN)
    lines.append(_header(
        "  🤖  AutoApply AI  —  Intelligent Job Hunter  ",
        f"  {user_name}  ·  {now.strftime('%A, %d %b %Y  %H:%M:%S')}  ·  query: '{query}'  "
    ))

    # ── System Status ───────────────────────────────────────────────────────
    lines.append(_section("System"))
    status_str = f"{BRED}PAUSED ⏸{RESET}" if is_paused else f"{BGREEN}RUNNING ▶{RESET}"
    lines.append(_kv("Status",      status_str,                        width=18))
    lines.append(_kv("Min Match",   f"{BCYAN}{min_match}%{RESET}",     width=18))
    lines.append(_kv("Daily Cap",   f"{BYELLOW}{daily_cap}/day{RESET}", width=18))
    lines.append(_kv("Aggressiveness", controls.get("aggressiveness", "normal"), width=18))
    lines.append(_kv("Platforms",   controls.get("platforms", "—"),    width=18))

    # ── Today's Progress ───────────────────────────────────────────────────
    lines.append(_section("Today's Progress"))
    bar = _bar(total_applied, daily_cap, width=24,
               color=BGREEN if total_applied < daily_cap else BYELLOW)
    lines.append(f"  {DIM}Applied today  {RESET}{bar}  {BCYAN}{total_applied}/{daily_cap}{RESET}")
    lines.append("")
    lines.append(f"  {BGREEN}✓ Applied    {RESET}{BWHITE}{today['applied']}{RESET}    "
                 f"{BYELLOW}~ Uncertain  {RESET}{BWHITE}{today['uncertain']}{RESET}    "
                 f"{BRED}✗ Failed     {RESET}{BWHITE}{today['failed']}{RESET}    "
                 f"{DIM}Remaining cap: {RESET}{BCYAN}{remaining_cap}{RESET}")

    # ── Queue Breakdown ────────────────────────────────────────────────────
    lines.append(_section("Queue"))
    total_q = sum(q_stats.values()) or 1
    for st in ("pending", "applied", "skip", "failed", "uncertain", "external_skip"):
        cnt = q_stats.get(st, 0)
        if cnt == 0:
            continue
        dot = _status_dot(st)
        bar = _bar(cnt, total_q, width=18, color={
            "applied": BGREEN, "pending": BYELLOW, "skip": DIM,
            "failed": BRED, "uncertain": BYELLOW, "external_skip": BLUE,
        }.get(st, BWHITE))
        lines.append(f"  {dot} {st:<14} {bar}  {BWHITE}{cnt}{RESET}")

    # ── Database Counts ────────────────────────────────────────────────────
    lines.append(_section("Database"))
    lines.append(
        f"  {DIM}Jobs:{RESET} {BWHITE}{db_counts.get('jobs',0)}{RESET}   "
        f"{DIM}Queue:{RESET} {BWHITE}{db_counts.get('apply_queue',0)}{RESET}   "
        f"{DIM}Outcomes:{RESET} {BWHITE}{db_counts.get('application_outcomes',0)}{RESET}   "
        f"{DIM}Companies:{RESET} {BWHITE}{db_counts.get('company_intelligence',0)}{RESET}"
    )

    # ── All-time Outcome Stats ─────────────────────────────────────────────
    if outcomes["total"] > 0:
        rate = outcomes["success"] / outcomes["total"] * 100
        lines.append("")
        lines.append(
            f"  {DIM}All-time:{RESET}  "
            f"{BGREEN}Applied: {outcomes['success']}{RESET}  "
            f"{BRED}Failed: {outcomes['failed']}{RESET}  "
            f"{BLUE}External: {outcomes['external']}{RESET}  "
            f"{BCYAN}Success Rate: {rate:.1f}%{RESET}"
        )

    # ── Top Matched Jobs ───────────────────────────────────────────────────
    if top_jobs:
        lines.append(_section("Top Matched Jobs"))
        for j in top_jobs:
            score  = j.get("match_score_at_apply")
            score_s = f"{score:5.1f}%" if score is not None else "  ?.?%"
            dot    = _status_dot(j.get("status", ""))
            title  = (j.get("title") or "Unknown")[:35]
            company= (j.get("company") or "")[:22]
            score_color = BGREEN if (score or 0) >= 60 else BYELLOW if (score or 0) >= 40 else BRED
            lines.append(
                f"  {dot} {score_color}{score_s}{RESET}  "
                f"{BWHITE}{title:<36}{RESET}  {DIM}{company}{RESET}"
            )

    # ── Recent Applications ────────────────────────────────────────────────
    if recent:
        lines.append(_section("Recent Applications"))
        for r in recent:
            status = r.get("status", "")
            dot    = _status_dot(status)
            title  = (r.get("title") or "?")[:35]
            company= (r.get("company") or "")[:20]
            ts_raw = r.get("updated_at") or ""
            # Format timestamp
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts_s = ts.astimezone().strftime("%d %b %H:%M")
            except Exception:
                ts_s = ts_raw[:16]
            lines.append(
                f"  {dot} {DIM}{ts_s}{RESET}  "
                f"{BWHITE}{title:<36}{RESET}  {DIM}{company}{RESET}"
            )

    # ── Last Cycle Info ────────────────────────────────────────────────────
    if last_cycle:
        lines.append(_section("Last Agent Cycle"))
        cid  = last_cycle.get("cycle_id", "—")
        dur  = last_cycle.get("duration_s", 0)
        err  = last_cycle.get("error")
        s    = last_cycle.get("scraper", {})
        m    = last_cycle.get("matcher", {})
        a    = last_cycle.get("apply_bot", {})
        fin  = last_cycle.get("finished_at", "")
        try:
            fin_dt = datetime.fromisoformat(fin.replace("Z", "+00:00"))
            ago    = datetime.now(timezone.utc) - fin_dt
            ago_s  = f"{int(ago.total_seconds() // 60)}m ago" if ago.total_seconds() < 3600 \
                     else f"{ago.total_seconds()/3600:.1f}h ago"
        except Exception:
            ago_s = fin[:16]
        lines.append(f"  {DIM}Cycle{RESET}  {BCYAN}{cid}{RESET}  {DIM}({ago_s}, {dur}s){RESET}")
        lines.append(
            f"  {DIM}Scraped{RESET} {BWHITE}{s.get('new_jobs',0)} new{RESET}   "
            f"{DIM}Scored{RESET} {BWHITE}{m.get('scored',0)}{RESET}   "
            f"{DIM}Applied{RESET} {BWHITE}{a.get('applied',0)}{RESET}   "
            f"{DIM}Failed{RESET} {BWHITE}{a.get('failed',0)}{RESET}"
        )
        if err:
            lines.append(f"  {BRED}Last error: {err}{RESET}")

    # ── Controls Help ──────────────────────────────────────────────────────
    lines.append("")
    lines.append(_rule())
    lines.append(
        f"  {DIM}[q] Quit   [p] Pause/Resume   [r] Reset Queue   "
        f"[s] Run Scraper   [m] Run Matcher   [a] Run Cycle{RESET}"
    )
    if refresh_interval > 0:
        lines.append(
            f"  {DIM}Auto-refresh every {refresh_interval}s  ·  "
            f"Last updated: {now.strftime('%H:%M:%S')}{RESET}"
        )
    lines.append("")

    return "\n".join(lines)


# ── Interactive Controls ──────────────────────────────────────────────────────

def _set_paused(paused: bool) -> None:
    val = "true" if paused else "false"
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE user_controls SET value=?, updated_at=CURRENT_TIMESTAMP WHERE key='paused'",
                (val,)
            )
            if not paused:
                # If resuming, clear the manual verification flag
                conn.execute("DELETE FROM user_controls WHERE key='manual_verification_required'")
        print(f"\n{'PAUSED ⏸' if paused else 'RESUMED ▶'}")
    except Exception as e:
        print(f"Error: {e}")

def _reset_queue() -> None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE apply_queue SET status='pending', match_score_at_apply=NULL")
        print("\nQueue reset — all jobs set to pending.")
    except Exception as e:
        print(f"Error: {e}")


# ── Main Loop ─────────────────────────────────────────────────────────────────

def run_dashboard(refresh: int = 5, once: bool = False) -> None:
    """
    Run the live dashboard.

    Args:
        refresh: Seconds between refreshes (0 = no auto-refresh).
        once:    Print once and exit.
    """
    # Enable Windows ANSI support
    if sys.platform == "win32":
        os.system("")  # Trick to enable ANSI in Windows terminal

    if once:
        print(render(refresh_interval=0))
        return

    print(HIDE_CURSOR, end="", flush=True)
    controls = fetch_controls()
    is_paused = controls.get("paused") == "true"

    # Non-blocking keypress thread (Windows-compatible)
    _cmd_queue = []
    _stop = threading.Event()

    def _key_listener():
        try:
            import msvcrt
            while not _stop.is_set():
                if msvcrt.kbhit():
                    ch = msvcrt.getwch().lower()
                    _cmd_queue.append(ch)
                time.sleep(0.1)
        except ImportError:
            pass  # Non-Windows — keypress not supported in simple mode

    key_thread = threading.Thread(target=_key_listener, daemon=True)
    key_thread.start()

    try:
        while True:
            # Handle keypress commands
            while _cmd_queue:
                ch = _cmd_queue.pop(0)
                if ch == "q":
                    print(SHOW_CURSOR)
                    print(CLEAR_SCREEN + f"\n{BWHITE}AutoApply AI dashboard closed.{RESET}\n")
                    _stop.set()
                    return

                elif ch == "p":
                    ctrl = fetch_controls()
                    currently_paused = ctrl.get("paused") == "true"
                    _set_paused(not currently_paused)
                    time.sleep(0.5)

                elif ch == "r":
                    _reset_queue()
                    time.sleep(1)

                elif ch == "s":
                    print(SHOW_CURSOR)
                    print(f"\n{BYELLOW}Running scraper...{RESET}")
                    try:
                        from finder.core.scraper import run_scraper
                        run_scraper()
                    except Exception as e:
                        print(f"{BRED}Scraper error: {e}{RESET}")
                    print(HIDE_CURSOR, end="", flush=True)

                elif ch == "m":
                    print(SHOW_CURSOR)
                    print(f"\n{BYELLOW}Running matcher...{RESET}")
                    try:
                        from finder.core.matcher import run_matcher
                        run_matcher()
                    except Exception as e:
                        print(f"{BRED}Matcher error: {e}{RESET}")
                    print(HIDE_CURSOR, end="", flush=True)

                elif ch == "a":
                    print(SHOW_CURSOR)
                    print(f"\n{BYELLOW}Running full agent cycle...{RESET}")
                    try:
                        from finder.core.agent import run_agent_cycle
                        run_agent_cycle()
                    except Exception as e:
                        print(f"{BRED}Agent error: {e}{RESET}")
                    print(HIDE_CURSOR, end="", flush=True)

            # Render dashboard
            sys.stdout.write(render(refresh_interval=refresh))
            sys.stdout.flush()

            if refresh <= 0:
                break

            time.sleep(refresh)

    except KeyboardInterrupt:
        pass
    finally:
        _stop.set()
        print(SHOW_CURSOR, end="")
        print(f"\n{BWHITE}Dashboard closed.{RESET}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoApply AI — Live Dashboard")
    parser.add_argument("--once",    action="store_true", help="Print once and exit")
    parser.add_argument("--refresh", type=int, default=5, help="Refresh interval in seconds")
    args = parser.parse_args()

    run_dashboard(refresh=args.refresh, once=args.once)
