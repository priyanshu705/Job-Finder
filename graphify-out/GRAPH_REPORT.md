# Graph Report - Finder  (2026-04-28)

## Corpus Check
- 71 files · ~52,365 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 337 nodes · 535 edges · 16 communities detected
- Extraction: 76% EXTRACTED · 24% INFERRED · 0% AMBIGUOUS · INFERRED: 128 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 62|Community 62]]

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 42 edges
2. `render()` - 17 edges
3. `q()` - 16 edges
4. `run_agent_cycle()` - 14 edges
5. `init_db()` - 11 edges
6. `run_dashboard()` - 10 edges
7. `run_sheets_sync()` - 10 edges
8. `_safe_query()` - 9 edges
9. `run_matcher()` - 9 edges
10. `sync_applications()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `get_status()` --calls--> `get_summary()`  [INFERRED]
  src\finder\core\agent\orchestrator.py → src\finder\shared\metrics.py
- `main()` --calls--> `run_dashboard()`  [INFERRED]
  run.py → src\finder\cli\dashboard.py
- `main()` --calls--> `get_db()`  [INFERRED]
  run.py → src\finder\shared\database.py
- `q()` --calls--> `get_db()`  [INFERRED]
  src\finder\api\main.py → src\finder\shared\database.py
- `add_goal()` --calls--> `get_db()`  [INFERRED]
  src\finder\api\main.py → src\finder\shared\database.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (45): delete_goal(), health(), Seed realistic demo data — idempotent, safe to call multiple times., resume(), seed_demo_data(), update_control(), update_feedback(), update_job_status() (+37 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (24): activity(), add_goal(), companies(), get_controls(), get_goals(), insights(), jobs(), pause() (+16 more)

### Community 2 - "Community 2"
Cohesion: 0.14
Nodes (29): _bar(), _box_bot(), _box_row(), _box_top(), _db(), fetch_controls(), fetch_db_counts(), fetch_last_cycle() (+21 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (25): trigger_scrape_visible(), _clean_text(), _enqueue_job(), _fetch_job_detail(), _get_existing_urls(), _insert_job(), is_logged_in(), login() (+17 more)

### Community 4 - "Community 4"
Cohesion: 0.2
Nodes (19): migrate(), check_db(), append_application_row(), _fmt_ts(), _get_client(), _get_or_create_tab(), _open_sheet(), src/finder/core/sheets/sync.py ----------------------------- Google Sheets Sync (+11 more)

### Community 5 - "Community 5"
Cohesion: 0.15
Nodes (16): generate_smart_answers(), Generate intelligent, tailored answers for common application questions., initialize_queries(), Seed the query_weights table based on detected roles., Adjust the weight of a query (e.g. +0.1 for apply, -0.2 for skip)., External entry point for feedback loop., record_feedback(), update_query_weight() (+8 more)

### Community 6 - "Community 6"
Cohesion: 0.17
Nodes (11): _get_controls(), get_status(), src/finder/core/agent/orchestrator.py ------------------------------------ Maste, Infinite loop for periodic agent execution., Returns the current system status for dashboard use., Executes a full agent cycle using a single browser session., run_agent_cycle(), run_agent_loop() (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.18
Nodes (13): extract_skills(), parse_resume(), src/finder/core/matcher/service.py --------------------------------- Resume ↔ Jo, Extract known tech skills from text using regex patterns only., Lowercase alphanum tokens, remove stop-words., Compute cosine similarity between two documents using TF-IDF weights.     Pure P, run_matcher(), score_job() (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.18
Nodes (6): _new_pg_conn(), _PGConn, _PGProxy, Context-manager that opens a connection and commits/rolls back., Open a fresh psycopg2 dict-cursor connection., Thin wrapper that makes psycopg2 feel like sqlite3 for our codebase.

### Community 10 - "Community 10"
Cohesion: 0.33
Nodes (1): ErrorBoundary

### Community 13 - "Community 13"
Cohesion: 0.6
Nodes (4): _format_answer(), generate_smart_answers(), _get_skill_intersection(), src/finder/core/apply_bot/answer_generator.py ----------------------------------

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (3): check(), main(), setup.py -------- Project setup verifier. Run this ONCE after cloning the repo t

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (1): src/finder/shared/retry.py -------------------------- Reusable retry decorator w

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): wsgi.py ------- WSGI entry point for Gunicorn (production).

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): src/finder/shared/config.py --------------------------- Centralized configuratio

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): psycopg2 doesn't populate lastrowid; callers that need the new PK             mu

## Knowledge Gaps
- **57 isolated node(s):** `run.py ------ Primary entry point for AutoApply AI.`, `setup.py -------- Project setup verifier. Run this ONCE after cloning the repo t`, `wsgi.py ------- WSGI entry point for Gunicorn (production).`, `src/finder/api/main.py ---------------------- AutoApply AI — Flask REST API`, `Convert a sqlite3.Row or psycopg2 RealDictRow to a plain dict.` (+52 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 10`** (6 nodes): `ErrorBoundary`, `.componentDidCatch()`, `.constructor()`, `.getDerivedStateFromError()`, `.render()`, `ErrorBoundary.jsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (3 nodes): `src/finder/shared/retry.py -------------------------- Reusable retry decorator w`, `retry()`, `retry.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `wsgi.py ------- WSGI entry point for Gunicorn (production).`, `wsgi.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (2 nodes): `src/finder/shared/config.py --------------------------- Centralized configuratio`, `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `psycopg2 doesn't populate lastrowid; callers that need the new PK             mu`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_db()` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `run_agent_cycle()` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `run_matcher()` connect `Community 7` to `Community 0`, `Community 2`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `get_db()` (e.g. with `main()` and `q()`) actually correct?**
  _`get_db()` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `q()` (e.g. with `get_db()` and `.fetchall()`) actually correct?**
  _`q()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `run_agent_cycle()` (e.g. with `main()` and `trigger_cycle()`) actually correct?**
  _`run_agent_cycle()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `run.py ------ Primary entry point for AutoApply AI.`, `setup.py -------- Project setup verifier. Run this ONCE after cloning the repo t`, `wsgi.py ------- WSGI entry point for Gunicorn (production).` to the rest of the system?**
  _57 weakly-connected nodes found - possible documentation gaps or missing edges._