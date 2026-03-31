import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = os.path.join("inventory_db", "digital_fte.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def clear_logs():
    """Archives old logs and clears current log files and DB entries."""
    print("🧹 Cleaning up old logs...")
    
    # 1. Archive DB Logs
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Move logs older than 7 days to an archive table or just delete for now as requested
        # For simplicity and to only show "new" errors, we'll clear the logs table
        cursor.execute("DELETE FROM logs")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ DB Log Clear Error: {e}")

    # 2. Archive and Clear Log Files
    LOG_DIR = "logs"
    ARCHIVE_DIR = os.path.join(LOG_DIR, "archive")
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for log_file in os.listdir(LOG_DIR):
        if log_file.endswith(".log"):
            file_path = os.path.join(LOG_DIR, log_file)
            if os.path.getsize(file_path) > 0:
                archive_path = os.path.join(ARCHIVE_DIR, f"{log_file}_{timestamp}.bak")
                try:
                    shutil.move(file_path, archive_path)
                    # Create empty new log file
                    open(file_path, 'w').close()
                except Exception as e:
                    print(f"❌ File Log Clear Error ({log_file}): {e}")

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Inventory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            image_url TEXT
        )
    ''')

    # Leads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            handle TEXT NOT NULL,
            message TEXT,
            reply_text TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            screenshot_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Campaigns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            features TEXT,
            ig_caption TEXT,
            tweet TEXT,
            image_prompt TEXT,
            image_url TEXT,
            status TEXT DEFAULT 'draft',
            ig_post_url TEXT,
            fb_post_url TEXT,
            twitter_post_url TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Customer Memory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT UNIQUE,
            history TEXT,
            last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Automated Posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS automated_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            post_content TEXT NOT NULL,
            status TEXT DEFAULT 'queued',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initialize default settings if not exists
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('manual_review', 'true')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('start_hour', '09')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('end_hour', '23')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('reply_on_instagram', 'false')")

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    # Ensure the directory exists
    os.makedirs("inventory_db", exist_ok=True)
    initialize_db()
