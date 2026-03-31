import asyncio
import os
import random
import logging
from datetime import datetime
from playwright.async_api import async_playwright
from database_manager import get_connection
from stealth_utils import HumanBehavior

# Logging Setup
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "whatsapp_poster.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
SESSION_FILE = os.path.join("whatsapp_session", "state.json")
USER_DATA_DIR = os.path.join("whatsapp_session", "browser_data")
HEADLESS = False # Set to False to see the QR code/browser for debugging

def get_ready_leads():
    """Fetch leads that are ready to be sent via WhatsApp."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, handle, reply_text FROM leads WHERE status = 'ready_to_whatsapp'")
    leads = cursor.fetchall()
    conn.close()
    return leads

def update_lead_status(lead_id, status):
    """Update lead status in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()

def log_action(action, status, screenshot_path=None):
    """Log system actions and screenshots to the logs table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (action, status, screenshot_path) VALUES (?, ?, ?)",
        (action, status, screenshot_path)
    )
    conn.commit()
    conn.close()

async def send_whatsapp_messages():
    logging.info("WhatsApp Poster is starting...")
    print("WhatsApp Poster is active. Press Ctrl+C to stop.")

    while True:
        # Check Working Hours
        if not HumanBehavior.is_active_hours():
            logging.info("Stealth Mode: System is in SLEEP mode due to active hours settings.")
            await asyncio.sleep(600) # Sleep for 10 minutes before checking again
            continue

        leads = get_ready_leads()
        
        if not leads:
            logging.info("No leads ready for WhatsApp. Waiting for 10 seconds...")
            await asyncio.sleep(10) # Wait 10 seconds before scanning again
            continue

        async with async_playwright() as p:
            # Use launch_persistent_context for better session maintenance
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            
            print(f"🚀 Launching Persistent Browser (Headless={HEADLESS})...")
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=USER_DATA_DIR,
                    headless=HEADLESS,
                    args=['--no-sandbox', '--disable-setuid-sandbox'],
                    user_agent=user_agent,
                    viewport={'width': 1280, 'height': 720}
                )
                page = await context.new_page()
            except Exception as launch_err:
                logging.error(f"Failed to launch persistent context: {launch_err}")
                break
            
            try:
                logging.info("Opening WhatsApp Web...")
                # Use domcontentloaded for faster check
                await page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=60000)
                
                # Smart Element Waiting: Wait for the search box or chat list
                try:
                    print("⏳ Waiting for WhatsApp interface to load...")
                    await page.wait_for_selector('div[contenteditable="true"][data-tab="3"], #side', timeout=60000)
                    print("✅ WhatsApp Web Loaded successfully.")
                except Exception:
                    logging.error("WhatsApp Web failed to load or session expired. If you see a QR code, please run init_sessions.py again.")
                    print("❌ Error: WhatsApp Session Expired or QR Code required.")
                    if not HEADLESS:
                        print("Window is open. You can check the status now.")
                        await asyncio.sleep(60) 
                    break

                for lead_id, handle, reply_content in leads:
                    try:
                        logging.info(f"Attempting to send message to: {handle}")
                        
                        # 1. Hover & Click the search box
                        await HumanBehavior.simulate_mouse_movement(page, 'div[contenteditable="true"][data-tab="3"]')
                        search_box = await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]')
                        await search_box.click()
                        await HumanBehavior.human_type(page, 'div[contenteditable="true"][data-tab="3"]', handle)
                        await asyncio.sleep(2)
                        
                        # 2. Press Enter to open the chat
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(3) # Wait for chat to open

                        # 3. Locate & Type in the message box
                        msg_box_selector = 'div[contenteditable="true"][data-tab="10"]'
                        message_box = await page.query_selector(msg_box_selector)
                        
                        if message_box:
                            await HumanBehavior.simulate_mouse_movement(page, msg_box_selector)
                            await message_box.click()
                            await HumanBehavior.human_type(page, msg_box_selector, reply_content)
                            await asyncio.sleep(1)
                            await page.keyboard.press("Enter")
                            
                            # TAKE SCREENSHOT FOR EVIDENCE
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            screenshot_path = os.path.join(LOG_DIR, f"success_wa_{lead_id}_{timestamp}.png")
                            await page.screenshot(path=screenshot_path)
                            
                            logging.info(f"✅ Message sent successfully. Screenshot: {screenshot_path}")
                            update_lead_status(lead_id, "completed")
                            log_action(f"WhatsApp sent to @{handle}", "Success", screenshot_path)
                            print(f"Sent: @{handle}")
                        else:
                            raise Exception("Chat box not found.")

                    except Exception as e:
                        logging.error(f"❌ Failed to send to {handle}: {e}")
                        screenshot_path = os.path.join(LOG_DIR, f"error_wa_{lead_id}_{datetime.now().strftime('%H%M%S')}.png")
                        await page.screenshot(path=screenshot_path)
                        update_lead_status(lead_id, "failed")
                        print(f"Failed: @{handle}")

                    # Anti-Ban: Stealth Random Jitter (45-150s)
                    await HumanBehavior.random_jitter()

            except Exception as e:
                logging.error(f"Critical WhatsApp Error: {e}")
            finally:
                await browser.close()

        # Wait a bit before next batch scan
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(send_whatsapp_messages())
