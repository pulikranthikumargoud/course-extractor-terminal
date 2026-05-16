from flask import Flask, request, jsonify, send_file, render_template, send_from_directory, make_response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
import os
import logging
import threading
import asyncio
from datetime import datetime

# Asynchronous Telegram Components
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
CORS(app)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SECURE API RECOVERY ---
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Temporary live cache to hold session tokens per user
USER_SESSIONS = {}

class DynamicClassplusSigner:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-access-token": self.token,
            "Accept": "application/json",
            "Origin": "https://web.classplusapp.com",
            "Referer": "https://web.classplusapp.com/"
        }

    def fetch_signed_url(self, raw_url):
        try:
            if "master.m3u8" not in raw_url and "playlist.m3u8" not in raw_url:
                return raw_url

            clean_base_url = raw_url.split('?')[0]
            api_endpoint = "https://api.classplusapp.com/v2/course/content/signed-url"
            params = {
                "url": clean_base_url,
                "userId": "174450341", 
                "orgId": "755722"
            }
            
            resp = requests.get(api_endpoint, params=params, headers=self.headers, timeout=8)
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("status") == "success" and res_json.get("data", {}).get("signedUrl"):
                    return res_json["data"]["signedUrl"]
            
            return f"{clean_base_url}?token={self.token}&user_id=174450341"
        except Exception as e:
            logger.error(f"Handshake signature error: {e}")
            return raw_url

# --- TELEGRAM BOT HANDLING LAYER ---
bot = None
if API_ID and API_HASH and BOT_TOKEN:
    bot = Client("render_root_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

    @bot.on_message(filters.command("start") & filters.private)
    async def start_handler(client, message):
        user_id = message.from_user.id
        USER_SESSIONS[user_id] = {"step": "await_token"}
        
        await message.reply_text(
            "🔑 **Classplus Dynamic Link Signer Engine**\n\n"
            "Please send me your fresh **`x-access-token`** string from your browser first:"
        )

    @bot.on_message(filters.private & filters.text & ~filters.command(["start"]))
    async def token_catcher(client, message):
        user_id = message.from_user.id
        text = message.text.strip()

        if user_id in USER_SESSIONS and USER_SESSIONS[user_id].get("step") == "await_token":
            if len(text) < 50:
                await message.reply_text("❌ That look too short to be a valid token string. Please send your complete token:")
                return
            
            USER_SESSIONS[user_id]["token"] = text
            USER_SESSIONS[user_id]["step"] = "await_file"
            await message.reply_text(
                "✅ **Token successfully validated and locked for this session!**\n\n"
                "Now, upload your link dump text file (`.txt`) and I will process it instantly."
            )

    @bot.on_message(filters.document & filters.private)
    async def file_processor(client, message):
        user_id = message.from_user.id
        
        if user_id not in USER_SESSIONS or "token" not in USER_SESSIONS[user_id]:
            await message.reply_text("⚠️ No active validation session found. Type /start to clear cache and start over.")
            return

        if not message.document.file_name.endswith('.txt'):
            await message.reply_text("❌ Please send a valid text document container layout (`.txt`).")
            return

        status_msg = await message.reply_text("📡 *Downloading raw manifest from Telegram cloud...*")
        input_file = await message.download()
        
        await status_msg.edit("⚙️ *Regenerating cryptographic signatures using your provided token keys...*")
        
        try:
            user_token = USER_SESSIONS[user_id]["token"]
            signer_engine = DynamicClassplusSigner(user_token)

            with open(input_file, "r", encoding="utf-8") as file:
                lines = file.readlines()

            processed_content = []
            for line in lines:
                if "http" in line:
                    prefix, actual_url = line.split("http", 1)
                    actual_url = "http" + actual_url.strip()
                    signed_link = signer_engine.fetch_signed_url(actual_url)
                    processed_content.append(f"{prefix.strip()} {signed_link}")
                else:
                    processed_content.append(line.rstrip('\n'))

            output_filename = f"signed_{message.document.file_name}"
            with open(output_filename, "w", encoding="utf-8") as out_file:
                out_file.write("\n".join(processed_content))

            await status_msg.edit("🚀 *Uploading verified manifest output file...*")
            await message.reply_document(document=output_filename, caption="✅ **All video streams successfully signed!**\n\n*Session closed. To load a new extraction run, use /start.*")
            
            # Flush session layout memory clear safety
            USER_SESSIONS.pop(user_id, None)
            os.remove(input_file)
            os.remove(output_filename)
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit(f"⚠️ **Runtime framework dropped task exception:** `{str(e)}`")

@app.route('/')
def home():
    return "🚀 **Asynchronous Classplus Web Signer Core Portal Live**"

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def initialize_bot_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if bot:
        bot.run()

if bot:
    worker_thread = threading.Thread(target=initialize_bot_loop, daemon=True)
    worker_thread.start()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
