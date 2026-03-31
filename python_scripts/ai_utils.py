import asyncio
import os
import requests
from google import genai
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# --- MOCK FALLBACKS ---
STATIC_PLACEHOLDER = os.path.join("inventory_db", "images", "images.jpg")
MOCK_CAPTION_TEMPLATE = "Check out our new {product} for only Rs. {price}! #Sales #AI #Ecommerce"
MOCK_TWEET_TEMPLATE = "New Arrival: {product} at Rs. {price}. Get yours now! 🚀 #ShopNow"

async def generate_with_retry(prompt, model_name="gemini-2.0-flash", retries=2, product_name="Product", price="0"):
    """Generates text with Gemini, or falls back to Mock Template if Quota Exceeded."""
    if MOCK_MODE:
        return MOCK_CAPTION_TEMPLATE.format(product=product_name, price=price)

    if not gemini_client: 
        return MOCK_CAPTION_TEMPLATE.format(product=product_name, price=price)

    for attempt in range(retries):
        try:
            response = gemini_client.models.generate_content(model=model_name, contents=prompt)
            return response.text.strip()
        except Exception as e:
            if "429" in str(e):
                print(f"🛑 Quota Hit (429). Waiting...")
                await asyncio.sleep(5) # Shorter wait for testing
            else:
                print(f"🤖 AI Error: {e}")
                break
    
    # FINAL FALLBACK
    print("⚠️ Fallback: Using Mock Caption due to API failure.")
    return MOCK_CAPTION_TEMPLATE.format(product=product_name, price=price)

async def generate_image_dalle(prompt, save_dir=os.path.join("inventory_db", "images")):
    """Generates image with DALL-E, or falls back to local placeholder if Quota Exceeded."""
    if MOCK_MODE:
        print(f"🛠️ MOCK MODE: Using placeholder image: {STATIC_PLACEHOLDER}")
        return STATIC_PLACEHOLDER

    if not openai_client:
        print("⚠️ OpenAI API Key missing. Using placeholder.")
        return STATIC_PLACEHOLDER
    
    try:
        os.makedirs(save_dir, exist_ok=True)
        print(f"🎨 Generating DALL-E 3 image...")
        
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1,
        )

        image_url = response.data[0].url
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"campaign_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)

        img_data = requests.get(image_url).content
        with open(filepath, 'wb') as handler:
            handler.write(img_data)
        
        return filepath

    except Exception as e:
        print(f"❌ DALL-E Error: {e}. Falling back to placeholder.")
        return STATIC_PLACEHOLDER
