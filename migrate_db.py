import sqlite3

def migrate():
    conn = sqlite3.connect('finder.db')
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(apply_queue)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    # Add assistant_data if missing
    if 'assistant_data' not in columns:
        print("Adding assistant_data column...")
        cursor.execute("ALTER TABLE apply_queue ADD COLUMN assistant_data TEXT")
    
    # Add match_score_at_apply if missing (just in case)
    if 'match_score_at_apply' not in columns:
        print("Adding match_score_at_apply column...")
        cursor.execute("ALTER TABLE apply_queue ADD COLUMN match_score_at_apply REAL")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
