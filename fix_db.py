import sqlite3
import os

DB_PATH = os.path.join("inventory_db", "digital_fte.db")

def fix_settings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = 'true' WHERE key = 'reply_on_instagram'")
    conn.commit()
    cursor.execute("SELECT value FROM settings WHERE key = 'reply_on_instagram'")
    print(f"IG Reply Setting: {cursor.fetchone()[0]}")
    conn.close()

if __name__ == "__main__":
    fix_settings()
