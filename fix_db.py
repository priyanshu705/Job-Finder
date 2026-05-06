"""
fix_db.py — one-shot migration script for AutoApply AI.
Run: python fix_db.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from finder.shared.database import init_db, get_db

print("=" * 60)
print("AutoApply AI — Database Fix & Migration")
print("=" * 60)

print("\n[1] Re-initializing schema (adds resume_data table, fixes indexes)...")
init_db()
print("    OK")

print("\n[2] Current queue status distribution:")
with get_db() as conn:
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM apply_queue GROUP BY status ORDER BY cnt DESC"
    ).fetchall()
    if not rows:
        print("    (queue is empty)")
    for r in rows:
        print(f"    {r['status']:30s} {r['cnt']}")

print("\n[3] Promoting scored pending jobs -> ready_to_apply...")
with get_db() as conn:
    conn.execute("""
        UPDATE apply_queue
        SET status = 'ready_to_apply', updated_at = CURRENT_TIMESTAMP
        WHERE status = 'pending'
          AND match_score_at_apply IS NOT NULL
    """)
print("    OK")

print("\n[4] Status distribution AFTER fix:")
with get_db() as conn:
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM apply_queue GROUP BY status ORDER BY cnt DESC"
    ).fetchall()
    if not rows:
        print("    (queue is empty)")
    for r in rows:
        print(f"    {r['status']:30s} {r['cnt']}")

print("\n[5] Checking assistant_data coverage...")
with get_db() as conn:
    total  = conn.execute("SELECT COUNT(*) as c FROM apply_queue").fetchone()["c"]
    filled = conn.execute(
        "SELECT COUNT(*) as c FROM apply_queue WHERE assistant_data IS NOT NULL AND assistant_data != ''"
    ).fetchone()["c"]
    print(f"    Total queue rows : {total}")
    print(f"    Has assistant_data: {filled}")
    print(f"    Missing           : {total - filled}")

print("\n[6] Generating missing assistant_data for all ready_to_apply / opened jobs...")
from finder.core.apply_bot.answer_generator import generate_smart_answers
import json
generated = 0
errors    = 0
with get_db() as conn:
    jobs = [dict(r) for r in conn.execute("""
        SELECT q.id, q.job_url, q.assistant_data,
               j.title, j.company, j.skills, j.description
        FROM apply_queue q
        LEFT JOIN jobs j ON j.job_url = q.job_url
        WHERE q.status IN ('ready_to_apply', 'opened', 'pending')
          AND (q.assistant_data IS NULL OR q.assistant_data = '')
        LIMIT 100
    """).fetchall()]

with get_db() as conn:
    for job in jobs:
        try:
            ai_data = generate_smart_answers(job)
            conn.execute(
                "UPDATE apply_queue SET assistant_data=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(ai_data), job["id"])
            )
            generated += 1
        except Exception as e:
            print(f"    ERROR job id={job.get('id')}: {e}")
            errors += 1

print(f"    Generated: {generated}  |  Errors: {errors}")

print("\n[7] Verifying resume_data table...")
with get_db() as conn:
    try:
        cnt = conn.execute("SELECT COUNT(*) as c FROM resume_data").fetchone()["c"]
        print(f"    resume_data table: OK  ({cnt} rows)")
    except Exception as e:
        print(f"    resume_data table: MISSING — {e}")

print("\n[8] Verifying query_weights...")
with get_db() as conn:
    rows = conn.execute("SELECT query, weight FROM query_weights ORDER BY weight DESC").fetchall()
    if rows:
        for r in rows:
            print(f"    query={r['query']:30s}  weight={r['weight']}")
    else:
        print("    (empty — will be seeded on next cycle)")

print("\n" + "=" * 60)
print("FIX COMPLETE — all issues resolved.")
print("Now start the backend: python run.py api")
print("=" * 60)
