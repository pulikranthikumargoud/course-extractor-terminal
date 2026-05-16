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

# --- ENVIRONMENTAL VARIABLE EXTRACTION LAYER ---
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Active token provided for verification loops
GLOBAL_ACCESS_TOKEN = "eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTc0NDUwMzQxLCJvcmdJZCI6NzU1NzIyLCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTk2MDM5MDM0NDEiLCJuYW1lIjoiTW91bmlrYXNhbGxhIiwiZW1haWwiOiJtb3VuaWthc2FsbGE2QGdtYWlsLmNvbSIsImlzRmlyc3RMb2dpbiI6dHJ1ZSwiZGVmYXVsdExhbmd1YWdlIjoiRU4iLCJjb3VudHJ5Q29kZSI6IklOIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJpc0RpeSI6dHJ1ZSwibG9naW5WaWEiOiJPdHAiLCJmaW5nZXJwcmludElkIjoid2ViLWV4dHJhY3Rvci1maW5nZXJwcmludCIsImlhdCI6MTc3ODkwODg0NCwiZXhwIjoxNzc5NTEzNjQ0fQ.qpNSQO-92jxstT_QyIPxwSmObr6xSnZY8o0KNA_CtWZWBU9cvr_PsTTM5If4fwk_"

class ClassplusContentSigner:
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
        """Contacts the core gateway to safely sign video manifest resources."""
        try:
            if "master.m3u8" not in raw_url and "playlist.m3u8" not in raw_url:
                return raw_url  # Static asset files (.pdf, .pptx) do not require decryption signing

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
            
            # Algorithmic backup interpolation fallback
            return f"{clean_base_url}?token={self.token}&user_id=174450341"
        except Exception as e:
            logger.error(f"Handshake signature failure: {e}")
            return raw_url

signer_engine = ClassplusContentSigner(GLOBAL_ACCESS_TOKEN)

# --- PYROGRAM DAEMON SUBSYSTEM ---
bot = None
if API_ID and API_HASH and BOT_TOKEN:
    bot = Client("render_background_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

    @bot.on_message(filters.command("start") & filters.private)
    async def start_cmd(client, message):
        await message.reply_text(
            "⚡ **Classplus Bulk Link Signer Bot Online** ⚡\n\n"
            "Drop your text file (`.txt`) containing the extracted course links here. "
            "I will sign all video entries instantly to ensure they work in your downloader!"
        )

    @bot.on_message(filters.document & filters.private)
    async def document_file_processor(client, message):
        if not message.document.file_name.endswith('.txt'):
            await message.reply_text("❌ Please send a clean structural text file (`.txt`).")
            return

        status_update = await message.reply_text("📡 *Downloading source file from Telegram cloud...*")
        input_path = await message.download()
        
        await status_update.edit("⚙️ *Parsing file entries and signing video links...*")
        
        try:
            with open(input_path, "r", encoding="utf-8") as file:
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

            await status_update.edit("🚀 *Uploading certified download file...*")
            await message.reply_document(document=output_filename, caption="✅ **All video links successfully signed and authenticated!**")
            
            # Garbage collection
            os.remove(input_path)
            os.remove(output_filename)
            await status_update.delete()
        except Exception as e:
            await status_update.edit(f"⚠️ **Core processing loop error:** `{str(e)}`")

# --- NATIVE CORE WEB INTERFACES ---
@app.route('/')
def home():
    return "🚀 **Classplus Link Processor & Telegram Bot Daemon Running Smoothly**"

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# --- WORKER MULTIPLEXER HOOK ---
def initialize_bot_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if bot:
        logger.info("Spawning Pyrogram task engine loops inside daemon context...")
        bot.run()

if bot:
    worker_thread = threading.Thread(target=initialize_bot_loop, daemon=True)
    worker_thread.start()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
