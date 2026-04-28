import argparse
from finder.core.agent import run_agent_cycle, run_agent_loop

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoApply AI — Autonomous Agent")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--loop", type=int, default=0, help="Interval in hours for loop mode")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser")
    args = parser.parse_args()

    if args.once:
        res = run_agent_cycle(headless=not args.visible)
        print(f"Cycle finished: {res}")
    elif args.loop > 0:
        run_agent_loop(interval_hours=args.loop)
    else:
        # Default to once if no loop specified
        res = run_agent_cycle(headless=not args.visible)
        print(f"Cycle finished: {res}")
