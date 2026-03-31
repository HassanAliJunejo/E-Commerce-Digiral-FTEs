import asyncio
import os
import random
import logging
import sqlite3
from google import genai
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
    filename=os.path.join(LOG_DIR, "instagram_watcher.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
SESSION_FILE = os.path.join("instagram_session", "state.json")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# KEYWORD LIST (To save API Quota)
INTENT_KEYWORDS = ['price', 'kya hai', 'delivery', 'available', 'stock', 'jacket', 'how much', 'rate', 'size', 'paisa', 'rupay']

def is_duplicate_lead(handle, message):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM leads WHERE handle = ? AND message = ? AND platform = 'Instagram'",
        (handle, message)
    )
    exists = cursor.fetchone()
    conn.close()
    return exists is not None

def is_ig_reply_enabled():
    """Check if 'Reply on Instagram' toggle is ON in DB."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'reply_on_instagram'")
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == 'true'
    except: return False

async def classify_intent_with_ai(comment_text, retries=2):
    # 1. LOCAL KEYWORD CHECK (Stealth Quota Protection)
    clean_msg = comment_text.lower()
    if any(keyword in clean_msg for keyword in INTENT_KEYWORDS):
        print(f"💡 KEYWORD MATCH: Direct lead detection for '{comment_text[:20]}...'")
        return True

    # 2. AI AS BACKUP
    if not client: return False
    prompt = f"Analyze this Instagram comment: '{comment_text}'. Does this comment show interest in product price, details, or an intention to buy? Respond ONLY with 'Yes' or 'No'."
    for attempt in range(retries):
        try:
            print(f"🤖 AI BACKUP: Analyzing intent (Attempt {attempt+1}) -> '{comment_text[:40]}...'")
            response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return "yes" in response.text.strip().lower()
        except Exception as e:
            if "429" in str(e):
                await asyncio.sleep(45)
            else: break
    return False

def update_lead_status(lead_id, status):
    """Update lead status in the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database Update Error: {e}")
        return False

async def save_lead(handle, message):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO leads (platform, handle, message, status) VALUES (?, ?, ?, ?)",
            ("Instagram", handle, message, "pending")
        )
        conn.commit()
        lead_id = cursor.lastrowid
        conn.close()
        print(f"✨✨✨ DHOOM MACHALE! ✨✨✨")
        print(f"✅ SUCCESS: Lead {lead_id} saved for @{handle}")
        return lead_id
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return None

async def reply_to_comment(page, element, handle, reply_text=None, lead_id=None):
    """Automatically click 'Reply', type a response, and send."""
    if page.is_closed():
        print("⚠️ Page is closed. Skipping reply.")
        return False
        
    try:
        print(f"💬 Attempting to Reply on Instagram to @{handle}...")
        
        # 1. Find and Click the 'Reply' button
        try:
            # Scroll into view before clicking to ensure visibility
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(1)

            # Prioritize ARIA labels and ROLES over simple text
            selectors = [
                'div[role="button"][aria-label="Reply"]',
                'button[aria-label="Reply"]',
                '[role="button"]:has-text("Reply")',
                '[aria-label="Reply"]',
                'button:has-text("Reply")',
                'span:has-text("Reply")'
            ]
            
            reply_button = None
            for selector in selectors:
                try:
                    reply_button = await element.query_selector(selector)
                    if reply_button:
                        print(f"🎯 Found 'Reply' button using selector: {selector}")
                        break
                except: continue
            
            if not reply_button:
                # Global fallback
                reply_button = page.get_by_text("Reply", exact=True).first
            
            if reply_button:
                # Wait and Click with explicit error handling
                await reply_button.wait_for_element_state("stable", timeout=10000)
                await HumanBehavior.simulate_mouse_movement(page, 'text="Reply"')
                await reply_button.click(timeout=10000)
                print(f"✅ 'Reply' clicked for @{handle}")
                await asyncio.sleep(2)
                
                # 2. Type the response
                if not reply_text:
                    reply_text = "Salam! We've sent you the details in DM/WhatsApp. Please check!"
                
                input_selector = 'section div[role="textbox"], textarea[placeholder*="Add a comment"], textarea[placeholder*="Reply"]'
                await page.wait_for_selector(input_selector, timeout=10000)
                await HumanBehavior.human_type(page, input_selector, reply_text)
                await asyncio.sleep(1)
                
                # 3. Press Enter to Post
                await page.keyboard.press("Enter")
                print(f"✅ Instagram Reply Posted to @{handle}")
                
                # 4. Update Status
                if lead_id:
                    update_lead_status(lead_id, "ready_to_whatsapp")
                return True
            else:
                print(f"⚠️ 'Reply' button NOT found for @{handle}.")
                return False
        except Exception as click_err:
            print(f"⚠️ Interaction Error (Reply): {click_err}")
            if "closed" in str(click_err).lower(): raise click_err # Trigger restart
            return False
            
    except Exception as e:
        print(f"❌ Instagram Reply Error: {e}")
        if "closed" in str(e).lower(): raise e # Trigger restart
        return False

async def monitor_instagram():
    while True: # Total persistence loop
        try:
            async with async_playwright() as p:
                if not os.path.exists(SESSION_FILE):
                    print("❌ ERROR: Session file missing.")
                    await asyncio.sleep(60)
                    continue

                print("🚀 Launching Instagram Watcher Engine...")
                browser = await p.chromium.launch(headless=False) 
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                context = await browser.new_context(storage_state=SESSION_FILE, user_agent=user_agent)
                page = await context.new_page()
                page.set_default_timeout(60000)

                # Navigation with Re-Launch logic
                try:
                    print("🔗 Navigating to Notifications...")
                    await page.goto("https://www.instagram.com/notifications/", wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_selector('div[role="main"], .x1lliihq', timeout=20000)
                    await asyncio.sleep(5)
                except Exception as nav_err:
                    print(f"⚠️ Initial Navigation Failed: {nav_err}. Restarting...")
                    await browser.close()
                    await asyncio.sleep(10)
                    continue

                while True: # Inner operational loop
                    try:
                        if page.is_closed(): break
                        
                        if "login" in page.url:
                            print("🛑 Session Expired. Restarting...")
                            break

                        if not HumanBehavior.is_active_hours():
                            await asyncio.sleep(600)
                            continue

                        print(f"🔍 Scanning Notifications at {datetime.now().strftime('%H:%M:%S')}...")
                        notification_elements = await page.query_selector_all('div[role="button"], div[role="gridcell"], .x1lliihq')
                        
                        seen_in_loop = set()
                        for element in notification_elements:
                            try:
                                if page.is_closed(): break
                                text = (await element.inner_text()).strip()
                                if not text or len(text) < 15 or text in seen_in_loop: continue
                                seen_in_loop.add(text)
                                
                                if any(kw in text.lower() for kw in ["commented", "replied", "tagged"]):
                                    clean_text = text.replace("\n", " ")
                                    words = clean_text.split()
                                    handle = words[0]
                                    if handle.lower() in ["new", "today"]: handle = words[1]
                                    handle = handle.replace(":", "").replace("@", "")
                                    
                                    # Check for existing smart replies
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT id, reply_text FROM leads WHERE handle = ? AND status = 'ready_to_insta_reply' ORDER BY timestamp DESC LIMIT 1", (handle,))
                                    smart_lead = cursor.fetchone()
                                    conn.close()

                                    if smart_lead:
                                        await reply_to_comment(page, element, handle, reply_text=smart_lead[1], lead_id=smart_lead[0])
                                    elif await classify_intent_with_ai(clean_text):
                                        lead_id = await save_lead(handle, clean_text)
                                        if is_ig_reply_enabled():
                                            await reply_to_comment(page, element, handle, lead_id=lead_id)
                                        await asyncio.sleep(5)
                            except Exception as e:
                                if "closed" in str(e).lower(): break
                                continue

                        await HumanBehavior.random_jitter(60, 150)
                        
                        try:
                            if not page.is_closed():
                                await page.reload(wait_until="domcontentloaded", timeout=60000)
                                await asyncio.sleep(10)
                        except Exception as reload_err:
                            print(f"⚠️ Reload failed: {reload_err}. Restarting context...")
                            break

                    except Exception as loop_err:
                        print(f"⚠️ Operational Loop Error: {loop_err}")
                        await asyncio.sleep(10)
                        if "closed" in str(loop_err).lower() or page.is_closed(): break

                await browser.close()

        except Exception as critical_err:
            print(f"🚨 CRITICAL SYSTEM CRASH: {critical_err}. Reconnecting in 10s...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(monitor_instagram())
