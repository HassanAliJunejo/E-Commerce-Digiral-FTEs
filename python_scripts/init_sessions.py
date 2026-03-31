import asyncio
import os
from playwright.async_api import async_playwright

# Configuration
SESSION_PATHS = {
    "instagram": os.path.join("instagram_session", "state.json"),
    "facebook": os.path.join("facebook_session", "state.json"),
    "whatsapp": os.path.join("whatsapp_session", "state.json"),
    "twitter": os.path.join("twitter_session", "state.json")
}

# Ensure directories exist
for path in SESSION_PATHS.values():
    os.makedirs(os.path.dirname(path), exist_ok=True)

async def verify_session(platform):
    """Verify if the session file is valid and still active."""
    state_path = SESSION_PATHS.get(platform)
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    
    if platform == "whatsapp":
        # WhatsApp uses persistent data dir
        user_data_dir = os.path.join("whatsapp_session", "browser_data")
        if not os.path.exists(user_data_dir):
            return False, "Browser data missing."
    elif not state_path or not os.path.exists(state_path):
        return False, "Session file missing."

    async with async_playwright() as p:
        try:
            if platform == "whatsapp":
                user_data_dir = os.path.join("whatsapp_session", "browser_data")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox'],
                    user_agent=user_agent
                )
            else:
                browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
                context = await browser.new_context(storage_state=state_path, user_agent=user_agent)
            
            page = await context.new_page()
            
            if platform == "instagram":
                await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
                is_valid = "login" not in page.url
            elif platform == "facebook":
                await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
                is_valid = "login" not in page.url
            elif platform == "whatsapp":
                await page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=60000)
                try:
                    await page.wait_for_selector('div[contenteditable="true"][data-tab="3"]', timeout=15000)
                    is_valid = True
                except:
                    is_valid = False
            elif platform == "twitter":
                await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
                is_valid = "login" not in page.url
            
            await context.close()
            if platform != "whatsapp": await browser.close()
            return is_valid, "Session is active." if is_valid else "Session expired or invalid."
        except Exception as e:
            return False, f"Verification failed: {e}"

async def login_and_save(platform, url):
    # Check if existing session is still valid
    print(f"\n🔍 Checking existing {platform.capitalize()} session...")
    is_valid, msg = await verify_session(platform)
    if is_valid:
        print(f"✅ {platform.capitalize()} session is already VALID. Skipping login.")
        return

    print(f"⚠️ {platform.capitalize()} {msg}")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    
    async with async_playwright() as p:
        print(f"\n--- Initializing {platform.capitalize()} Login ---")
        
        if platform == "whatsapp":
            user_data_dir = os.path.join("whatsapp_session", "browser_data")
            os.makedirs(user_data_dir, exist_ok=True)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                user_agent=user_agent
            )
        else:
            browser = await p.chromium.launch(headless=False, args=['--no-sandbox', '--disable-setuid-sandbox'])
            context = await browser.new_context(user_agent=user_agent)
            
        page = await context.new_page()
        
        print(f"Opening {url}...")
        try:
            await page.goto(url)
            print("Please complete the login manually in the browser window.")
            print("The script will wait until you are logged in or 2 minutes pass.")
            
            # Smart wait: check for success indicators
            for _ in range(24): # 24 * 5s = 120s
                await asyncio.sleep(5)
                current_url = page.url
                if platform == "whatsapp" and await page.query_selector('div[contenteditable="true"][data-tab="3"]'):
                    break
                if platform != "whatsapp" and "login" not in current_url and url not in current_url:
                    break
            
            # Save storage state for all (as backup for WA, primary for others)
            state_path = SESSION_PATHS[platform]
            await context.storage_state(path=state_path)
            print(f"✅ SUCCESS: {platform.capitalize()} session saved.")
            
        except Exception as e:
            print(f"❌ ERROR: Failed to save session for {platform}: {e}")
        finally:
            await context.close()
            if platform != "whatsapp": await browser.close()

async def main():
    print("Select the platform you want to log in to:")
    print("1. Instagram")
    print("2. Facebook")
    print("3. WhatsApp")
    print("4. Twitter")
    print("5. All")
    
    choice = input("Enter your choice (1/2/3/4/5): ")
    
    if choice == "1":
        await login_and_save("instagram", "https://www.instagram.com/accounts/login/")
    elif choice == "2":
        await login_and_save("facebook", "https://www.facebook.com/login/")
    elif choice == "3":
        await login_and_save("whatsapp", "https://web.whatsapp.com/")
    elif choice == "4":
        await login_and_save("twitter", "https://x.com/login")
    elif choice == "5":
        await login_and_save("instagram", "https://www.instagram.com/accounts/login/")
        await login_and_save("facebook", "https://www.facebook.com/login/")
        await login_and_save("whatsapp", "https://web.whatsapp.com/")
        await login_and_save("twitter", "https://x.com/login")
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    asyncio.run(main())
