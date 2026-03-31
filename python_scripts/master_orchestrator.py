import asyncio
import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from database_manager import get_connection
from ai_utils import generate_with_retry

# Load environment variables
load_dotenv()

# Logging Setup
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "orchestrator.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# FALLBACK STATIC MESSAGE (Quota Savior)
STATIC_FALLBACK = "Salam! Humaray paas variety mojood hai, aap batayein aapko kya chahiye? Humaray agent aap se jald mazeed raabta karenge."

def get_all_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, stock FROM inventory")
    products = [{"name": r[0], "price": r[1], "stock": r[2]} for r in cursor.fetchall()]
    conn.close()
    return products

def get_pending_leads():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, platform, handle, message FROM leads WHERE status = 'pending'")
    leads = cursor.fetchall()
    conn.close()
    return leads

def get_customer_memory(handle):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT history FROM customer_memory WHERE handle = ?", (handle,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def update_customer_memory(handle, new_msg):
    conn = get_connection()
    cursor = conn.cursor()
    history = get_customer_memory(handle)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"[{timestamp}] Msg: {new_msg}"
    if history:
        updated_history = f"{history}\n{entry}"
        cursor.execute("UPDATE customer_memory SET history = ?, last_interaction = CURRENT_TIMESTAMP WHERE handle = ?", (updated_history, handle))
    else:
        cursor.execute("INSERT INTO customer_memory (handle, history) VALUES (?, ?)", (handle, entry))
    conn.commit()
    conn.close()

def is_manual_review_on():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'manual_review'")
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 'true'

async def match_product_and_generate_reply(lead_data, products, history=None):
    product_list_str = "\n".join([f"- {p['name']} (Price: {p['price']}, Stock: {p['stock']})" for p in products])
    
    # 1. Match Product
    match_prompt = f"""
    You are an Inventory Expert. Identify if the user's message matches any product in our inventory.
    Inventory:
    {product_list_str}
    
    User Message: "{lead_data['message']}"
    
    Return ONLY the exact name of the product if matched, or 'No Match'.
    """
    
    matched_name = await generate_with_retry(match_prompt)
    if matched_name == "QUOTA_EXCEEDED": return None, STATIC_FALLBACK, "Quota Fallback"

    product = None
    if matched_name and matched_name != "No Match":
        product = next((p for p in products if p['name'].lower() in matched_name.lower()), None)

    # 2. Response Logic
    whatsapp_number = "923141023549" 
    
    if product:
        from urllib.parse import quote
        encoded_name = quote(product['name'])
        wa_link = f"https://wa.me/{whatsapp_number}?text=Hi,%20I%20want%20to%20buy%20{encoded_name}"
        
        if product['stock'] > 0:
            # In Stock Logic - Professional Funnel Template
            reply = f"Salam! {product['name']} ki price Rs. {product['price']} hai. Mazeed details aur 10% discount ke liye is link par click karein: {wa_link}"
            return product, reply, "Success"
        else:
            # Out of Stock Logic
            alternatives = [p for p in products if p['name'] != product['name'] and p['stock'] > 0]
            alt_str = alternatives[0]['name'] if alternatives else "other items"
            
            reply = f"Salam! {product['name']} filhal out of stock hai, lekin humaray paas {alt_str} available hai. Details ke liye WhatsApp karein: {wa_link}"
            return product, reply, "Success"
    else:
        # General Reply Logic (Fallback)
        wa_link = f"https://wa.me/{whatsapp_number}?text=Hi,%20I%20am%20interested%20in%20your%20products"
        gen_prompt = f"Write a friendly Hinglish general reply for customer: '{lead_data['message']}'. We are an e-commerce store. Ask them to contact on WhatsApp for quick help: {wa_link}"
        reply = await generate_with_retry(gen_prompt)
        if reply == "QUOTA_EXCEEDED": return None, STATIC_FALLBACK, "Quota Fallback"
        return None, reply, "General Reply"

def update_lead(lead_id, status, reply_text=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if reply_text:
            cursor.execute("UPDATE leads SET status = ?, reply_text = ? WHERE id = ?", (status, reply_text, lead_id))
        else:
            cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ DB Update Error: {e}")
        return False

async def orchestrate():
    print("🚀 Master Orchestrator (5-min Delay Quota Savior) Active.")
    
    while True:
        leads = get_pending_leads()
        products = get_all_products()
        
        for lead in leads:
            lead_id, platform, handle, message = lead
            print(f"🔄 Processing lead {lead_id} from @{handle}...")
            
            history = get_customer_memory(handle)
            lead_data = {"platform": platform, "message": message, "handle": handle}
            product, reply, result = await match_product_and_generate_reply(lead_data, products, history)
            
            # Professional Funnel: Instagram leads go to 'ready_to_insta_reply' first
            if platform == "Instagram":
                target_status = "ready_to_insta_reply"
            else:
                target_status = "ready_to_whatsapp"
                
            if is_manual_review_on():
                target_status = "waiting_approval"
            
            if result in ["Success", "General Reply", "Quota Fallback"]:
                if update_lead(lead_id, target_status, reply):
                    update_customer_memory(handle, f"Reply: {reply}")
                    print(f"✅ Lead {lead_id} updated to '{target_status}'.")
                else:
                    print(f"⚠️ Failed to update lead {lead_id}.")
            elif result == "Out of Stock":
                update_lead(lead_id, "out_of_stock")
            else:
                update_lead(lead_id, "pending_manual_review")
                
            await asyncio.sleep(5)

        # 🚀 5-MINUTE DELAY (Quota Savior)
        print("🕒 Waiting 5 minutes for next lead scan...")
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(orchestrate())
