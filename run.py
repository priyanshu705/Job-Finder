"""
run.py
------
Primary entry point for AutoApply AI.
"""

import os
import sys
import argparse

# Add 'src' to sys.path to enable 'import finder'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

def main():
    parser = argparse.ArgumentParser(description="AutoApply AI — Intelligent Job Automation")
    parser.add_argument("module", choices=["api", "dashboard", "agent", "setup", "reset", "resume"], help="Module to run")
    parser.add_argument("--once", action="store_true", help="Run once and exit (for agent)")
    parser.add_argument("--no-headless", action="store_true", help="Show the browser during automation")
    args, unknown = parser.parse_known_args()

    # Convert flag correctly: headless = not args.no_headless
    headless = not args.no_headless

    if args.module == "api":
        from finder.api.main import app
        port = int(os.getenv("API_PORT", 5000))
        host = os.getenv("API_HOST", "127.0.0.1")
        debug_mode = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
        if debug_mode:
            print("🚀 Running in DEBUG mode with auto-reload...")
        app.run(host=host, port=port, debug=debug_mode, use_reloader=debug_mode)
        
    elif args.module == "dashboard":
        from finder.cli.dashboard import run_dashboard
        run_dashboard()
        
    elif args.module == "agent":
        from finder.core.agent.orchestrator import run_agent_cycle, run_agent_loop
        if args.once:
            run_agent_cycle(headless=headless)
        else:
            run_agent_loop(headless=headless)
            
    elif args.module == "setup":
        import setup
        setup.main()

    elif args.module == "reset":
        from finder.shared.database import get_db
        with get_db() as conn:
            conn.execute("UPDATE apply_queue SET status='pending', match_score_at_apply=NULL")
        print("Queue reset successfully.")

    elif args.module == "resume":
        from finder.shared.database import get_db
        with get_db() as conn:
            conn.execute("UPDATE user_controls SET value='false' WHERE key='paused'")
            conn.execute("DELETE FROM user_controls WHERE key='manual_verification_required'")
        print("System resumed. Paused state and manual verification flags cleared.")

if __name__ == "__main__":
    main()
