import os
import sqlite3
from typing import List, Dict
from python_scripts.ai_utils import generate_with_retry

# Since we don't have ChromaDB in requirements.txt, 
# we'll use a SQLite-based fallback for the knowledge base 
# or a simple keyword-based retriever for this MVP.
# In a real scenario, you'd use chromadb.

class SimpleVectorEngine:
    def __init__(self, db_path="inventory_db/knowledge_base.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                content TEXT,
                metadata TEXT
            )
        """)
        # Seed some initial data if empty
        cursor.execute("SELECT COUNT(*) FROM knowledge")
        if cursor.fetchone()[0] == 0:
            seed_data = [
                ('shipping', 'We ship all products within 24-48 hours via TCS or Leopards. Delivery takes 3-5 working days.', '{"policy": "shipping"}'),
                ('returns', '7-day replacement warranty if the product is defective.', '{"policy": "returns"}'),
                ('payment', 'We accept Cash on Delivery (COD) and Bank Transfers.', '{"policy": "payment"}'),
                ('product_f15', 'The F15 Smartwatch has a 1.9 inch AMOLED display, heart rate monitoring, and 7-day battery life.', '{"product": "F15 Smartwatch", "price": "4500"}')
            ]
            cursor.executemany("INSERT INTO knowledge (category, content, metadata) VALUES (?, ?, ?)", seed_data)
        conn.commit()
        conn.close()

    def query(self, text: str, top_k=2) -> str:
        """Simple keyword-based retrieval for demonstration."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Search for words in content
        words = text.lower().split()
        results = []
        for word in words:
            if len(word) < 3: continue
            cursor.execute("SELECT content FROM knowledge WHERE content LIKE ?", (f'%{word}%',))
            rows = cursor.fetchall()
            for row in rows:
                if row[0] not in results:
                    results.append(row[0])
        
        conn.close()
        return "\n".join(results[:top_k])

# Singleton instance
vector_engine = SimpleVectorEngine()
