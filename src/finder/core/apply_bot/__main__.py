import argparse
from finder.core.apply_bot import run_apply_bot

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoApply AI — Apply Bot")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser")
    parser.add_argument("--cap", type=int, default=0, help="Daily cap")
    args = parser.parse_args()

    stats = run_apply_bot(headless=not args.visible, daily_cap=args.cap)
    print(f"Apply Bot finished: {stats}")
