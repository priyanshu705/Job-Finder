import argparse
from finder.core.scraper import run_scraper

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finder V6 — Job Scraper")
    parser.add_argument("--query", type=str, default="", help="Search query")
    parser.add_argument("--pages", type=int, default=0, help="Max pages")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser")
    args = parser.parse_args()

    stats = run_scraper(query=args.query, max_pages=args.pages, headless=not args.visible)
    print(f"Scraper finished: {stats}")
