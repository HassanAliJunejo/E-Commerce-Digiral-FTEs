import sqlite3
import os

DB_PATH = os.path.join("inventory_db", "digital_fte.db")
if not os.path.exists(DB_PATH):
    print(f"Database file NOT FOUND at {DB_PATH}")
else:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables in {DB_PATH}: {[t[0] for t in tables]}")
    conn.close()
