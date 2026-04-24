import argparse
from finder.core.matcher import run_matcher

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finder V6 — Resume Matcher")
    parser.add_argument("--resume", type=str, default="", help="Path to resume")
    parser.add_argument("--min-match", type=float, default=0.0, help="Min match threshold")
    args = parser.parse_args()

    stats = run_matcher(resume_path=args.resume, min_match=args.min_match)
    print(f"Matcher finished: {stats}")
