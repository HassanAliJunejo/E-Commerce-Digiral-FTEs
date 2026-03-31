import asyncio
import random
import logging
from datetime import datetime
import sqlite3
import os

DB_PATH = os.path.join("inventory_db", "digital_fte.db")

class HumanBehavior:
    @staticmethod
    async def random_jitter(min_sec=45, max_sec=150):
        """Wait for a random duration to mimic human pauses."""
        delay = random.randint(min_sec, max_sec)
        logging.info(f"Stealth Mode: Sleeping for {delay} seconds...")
        await asyncio.sleep(delay)

    @staticmethod
    def is_active_hours():
        """Check if the current time is within user-defined working hours."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key='start_hour'")
            start_h = int(cursor.fetchone()[0])
            cursor.execute("SELECT value FROM settings WHERE key='end_hour'")
            end_h = int(cursor.fetchone()[0])
            conn.close()

            current_h = datetime.now().hour
            return start_h <= current_h < end_h
        except Exception as e:
            logging.error(f"Stealth Mode (Active Hours Error): {e}")
            return True # Default to active if error

    @staticmethod
    async def simulate_mouse_movement(page, selector):
        """Hover over an element before clicking to mimic a human user."""
        try:
            element = await page.wait_for_selector(selector)
            box = await element.bounding_box()
            if box:
                # Move to a random point within the element's box
                x = box['x'] + random.randint(5, int(box['width'] - 5))
                y = box['y'] + random.randint(5, int(box['height'] - 5))
                await page.mouse.move(x, y, steps=random.randint(5, 15))
                await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logging.warning(f"Stealth Mode (Mouse Simulation Failed): {e}")

    @staticmethod
    async def human_type(page, selector, text):
        """Type text with variable speed to mimic human typing."""
        await page.focus(selector)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.2))
