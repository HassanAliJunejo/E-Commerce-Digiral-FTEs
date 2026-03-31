import asyncio
import os
import sqlite3
import logging
from playwright.async_api import async_playwright
from database_manager import get_connection

# Logging Setup
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "multi_platform_poster.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

SESSION_PATHS = {
    "IG": os.path.join("instagram_session", "state.json"),
    "FB": os.path.join("facebook_session", "state.json"),
    "Twitter": os.path.join("twitter_session", "state.json")
}

async def post_to_instagram(page, caption, image_path=None):
    logging.info("Attempting to post to Instagram...")
    await page.goto("https://www.instagram.com/")
    await asyncio.sleep(5)
    
    try:
        # Simplified flow: This depends on the IG UI version (mobile vs desktop)
        # Often 'New Post' button is [aria-label='New post'] or similar
        await page.click("svg[aria-label='New post']")
        await asyncio.sleep(2)
        
        if image_path and os.path.exists(image_path):
            # Handle file upload
            async with page.expect_file_chooser() as fc_info:
                await page.click("button:has-text('Select from computer')")
            file_chooser = await fc_info.value
            await file_chooser.set_files(image_path)
            await asyncio.sleep(3)
            
            await page.click("button:has-text('Next')")
            await asyncio.sleep(2)
            await page.click("button:has-text('Next')")
            await asyncio.sleep(2)
            
            await page.fill("div[aria-label='Write a caption...']", caption)
            await page.click("button:has-text('Share')")
            await asyncio.sleep(10)
            
            logging.info("Successfully posted to Instagram")
            return page.url # This might not be the direct post URL immediately
        else:
            logging.warning("No image provided for Instagram post.")
            return None
    except Exception as e:
        logging.error(f"Failed to post to Instagram: {e}")
        return None

async def post_to_facebook(page, caption, image_path=None):
    logging.info("Attempting to post to Facebook...")
    await page.goto("https://www.facebook.com/")
    await asyncio.sleep(5)
    
    try:
        # Click 'What's on your mind?'
        await page.click("text=What's on your mind?")
        await asyncio.sleep(3)
        
        await page.fill("div[aria-label^='What\\'s on your mind']", caption)
        
        if image_path and os.path.exists(image_path):
            # Click Photo/Video icon
            await page.click("aria-label='Photo/video'")
            await asyncio.sleep(2)
            # Find the input[type=file]
            async with page.expect_file_chooser() as fc_info:
                await page.click("text=Add photos/videos")
            file_chooser = await fc_info.value
            await file_chooser.set_files(image_path)
            await asyncio.sleep(3)
        
        await page.click("div[aria-label='Post']")
        await asyncio.sleep(10)
        
        logging.info("Successfully posted to Facebook")
        return page.url
    except Exception as e:
        logging.error(f"Failed to post to Facebook: {e}")
        return None

async def post_to_twitter(page, caption, image_path=None):
    logging.info("Attempting to post to Twitter/X...")
    await page.goto("https://x.com/home")
    await asyncio.sleep(5)
    
    try:
        await page.fill("div[aria-label='Post text']", caption)
        
        if image_path and os.path.exists(image_path):
            async with page.expect_file_chooser() as fc_info:
                await page.click("aria-label='Add photos or video'")
            file_chooser = await fc_info.value
            await file_chooser.set_files(image_path)
            await asyncio.sleep(3)
            
        await page.click("button[data-testid='tweetButtonInline']")
        await asyncio.sleep(5)
        
        logging.info("Successfully posted to Twitter")
        return page.url
    except Exception as e:
        logging.error(f"Failed to post to Twitter: {e}")
        return None

async def run_poster(campaign_id, platforms):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, price, ig_caption, tweet, image_url FROM campaigns WHERE id = ?", (campaign_id,))
    row = cursor.fetchone()
    
    if not row:
        logging.error(f"Campaign {campaign_id} not found.")
        return
    
    p_name, price, ig_caption, tweet, image_url = row
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Keep visible for now
        
        results = {}
        
        for plat in platforms:
            state_path = SESSION_PATHS.get(plat)
            if not state_path or not os.path.exists(state_path):
                logging.warning(f"Session not found for {plat}. Skipping.")
                continue
            
            context = await browser.new_context(storage_state=state_path)
            page = await context.new_page()
            
            if plat == "IG":
                url = await post_to_instagram(page, ig_caption, image_url)
                results['ig_post_url'] = url
            elif plat == "FB":
                url = await post_to_facebook(page, ig_caption, image_url)
                results['fb_post_url'] = url
            elif plat == "Twitter":
                url = await post_to_twitter(page, tweet, image_url)
                results['twitter_post_url'] = url
            
            await context.close()
        
        # Update database
        update_query = "UPDATE campaigns SET status = 'posted'"
        params = []
        for col, val in results.items():
            if val:
                update_query += f", {col} = ?"
                params.append(val)
        update_query += " WHERE id = ?"
        params.append(campaign_id)
        
        cursor.execute(update_query, tuple(params))
        conn.commit()
        conn.close()
        
        await browser.close()
        logging.info(f"Finished processing campaign {campaign_id}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python multi_platform_poster.py <campaign_id> <platforms_comma_separated>")
    else:
        c_id = int(sys.argv[1])
        plats = sys.argv[2].split(",")
        asyncio.run(run_poster(c_id, plats))
