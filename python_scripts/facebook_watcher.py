import asyncio
import os
import random
import logging
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from database_manager import get_connection
from stealth_utils import HumanBehavior

# Load environment variables
load_dotenv()

# Logging Setup
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "facebook_watcher.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
SESSION_FILE = os.path.join("facebook_session", "state.json")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def is_duplicate_lead(handle, message):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM leads WHERE handle = ? AND message = ? AND platform = 'Facebook'",
        (handle, message)
    )
    exists = cursor.fetchone()
    conn.close()
    return exists is not None

async def classify_intent_with_ai(comment_text):
    prompt = f"Analyze this Facebook comment: '{comment_text}'. Does this comment show interest in buying a product or asking for price? Respond 'Yes' or 'No'."
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        return "yes" in response.text.strip().lower()
    except: return False

async def save_lead(handle, message):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO leads (platform, handle, message, status) VALUES (?, ?, ?, ?)",
            ("Facebook", handle, message, "pending")
        )
        conn.commit()
        conn.close()
        logging.info(f"✅ Lead Saved: @{handle} (Facebook)")
    except Exception as e:
        logging.error(f"Database Error: {e}")

async def monitor_facebook():
    async with async_playwright() as p:
        if not os.path.exists(SESSION_FILE):
            print("Error: Facebook session missing.")
            return

        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=SESSION_FILE)
        page = await context.new_page()

        try:
            # Monitoring Facebook Business Suite or Notifications
            target_url = "https://www.facebook.com/notifications/"
            await page.goto(target_url)
            
            while True:
                if not HumanBehavior.is_active_hours():
                    logging.info("Stealth Mode: Facebook Watcher Sleeping...")
                    await asyncio.sleep(600)
                    continue

                logging.info("Scanning Facebook Notifications...")
                await page.wait_for_timeout(5000)

                # Simplified Facebook selector - might need adjustment based on UI
                notifications = await page.query_selector_all('div[role="gridcell"]')
                for notif in notifications:
                    try:
                        text = await notif.inner_text()
                        if "commented" in text.lower():
                            # Extract handle and message logic
                            handle = text.split(" ")[0]
                            if not is_duplicate_lead(handle, text):
                                if await classify_intent_with_ai(text):
                                    await save_lead(handle, text)
                    except: continue

                await HumanBehavior.random_jitter(180, 400)
                await page.reload()
        except Exception as e:
            logging.error(f"FB Watcher Crash: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(monitor_facebook())
