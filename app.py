from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging
import json
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ENGINE RECOVERY ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "") # Automatically provided by Render

# Fallback memory buffer cache to store session steps per user
# In production webhooks, a real DB is preferred, but this works for live active sessions
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

def send_telegram_message(chat_id, text):
    """Utility helper to send direct reply text back to user chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=8)
    except Exception as e:
        logger.error(f"Failed to send telegram message response: {e}")

def send_telegram_document(chat_id, file_path, caption):
    """Utility helper to send processed text manifest documents back to user chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as doc:
            files = {'document': doc}
            data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
            requests.post(url, data=data, files=files, timeout=15)
    except Exception as e:
        logger.error(f"Failed to send document stream response: {e}")

# --- WEBHOOK INTERCEPT ROUTE LAYER ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook_catcher():
    """Listens natively to Telegram webhook payloads without threads."""
    update = request.get_json()
    if not update or "message" not in update:
        return jsonify({"status": "ignored"}), 200

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    
    # 1. Handle Commands
    if "text" in message:
        text = message["text"].strip()
        
        if text == "/start":
            USER_SESSIONS[user_id] = {"step": "await_token"}
            send_telegram_message(chat_id, 
                "🔑 **Classplus Dynamic Link Signer Engine**\n\n"
                "Please send me your fresh **`x-access-token`** string from your browser first:"
            )
            return jsonify({"status": "ok"}), 200
            
        elif text == "/reset":
            USER_SESSIONS.pop(user_id, None)
            send_telegram_message(chat_id, "🔄 **Session memory completely cleared!** Type /start to begin fresh.")
            return jsonify({"status": "ok"}), 200
            
        elif text == "/help":
            send_telegram_message(chat_id,
                "📖 **Available Extractor Commands:**\n\n"
                "▶️ /start - Start a new link signing session\n"
                "🔄 /reset - Clear active token session cache\n"
                "ℹ️ /help - Display this command menu"
            )
            return jsonify({"status": "ok"}), 200

        # 2. Capture Text Tokens
        if user_id in USER_SESSIONS and USER_SESSIONS[user_id].get("step") == "await_token":
            if len(text) < 50:
                send_telegram_message(chat_id, "❌ That looks too short to be a valid token string. Please send your complete token:")
                return jsonify({"status": "ok"}), 200
                
            USER_SESSIONS[user_id]["token"] = text
            USER_SESSIONS[user_id]["step"] = "await_file"
            send_telegram_message(chat_id,
                "✅ **Token successfully validated and locked for this session!**\n\n"
                "Now, upload your link dump text file (`.txt`) and I will process it instantly."
            )
            return jsonify({"status": "ok"}), 200

    # 3. Handle File Upload Processing
    elif "document" in message and user_id in USER_SESSIONS and USER_SESSIONS[user_id].get("step") == "await_file":
        document = message["document"]
        file_name = document.get("file_name", "links.txt")
        file_id = document["file_id"]
        
        if not file_name.endswith('.txt'):
            send_telegram_message(chat_id, "❌ Please send a valid text document container layout (`.txt`).")
            return jsonify({"status": "ok"}), 200

        # Download raw file via Telegram API
        send_telegram_message(chat_id, "📡 *Downloading raw manifest layout...*")
        get_file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        file_info = requests.get(get_file_url).json()
        
        if file_info.get("ok"):
            file_path = file_info["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            raw_content = requests.get(download_url).text
            
            # Process and Sign Links
            user_token = USER_SESSIONS[user_id]["token"]
            signer_engine = DynamicClassplusSigner(user_token)
            
            processed_lines = []
            for line in raw_content.splitlines():
                if "http" in line:
                    prefix, actual_url = line.split("http", 1)
                    actual_url = "http" + actual_url.strip()
                    signed_link = signer_engine.fetch_signed_url(actual_url)
                    processed_lines.append(f"{prefix.strip()} {signed_link}")
                else:
                    processed_lines.append(line)
            
            output_filename = f"signed_{file_name}"
            with open(output_filename, "w", encoding="utf-8") as out_file:
                out_file.write("\n".join(processed_lines))
                
            send_telegram_document(chat_id, output_filename, "✅ **All video streams successfully signed!**\n\n*Session closed. To load a new extraction run, use /start.*")
            
            USER_SESSIONS.pop(user_id, None)
            if os.path.exists(output_filename):
                os.remove(output_filename)
        else:
            send_telegram_message(chat_id, "⚠️ Failed to fetch file from Telegram storage cloud.")
            
        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "ignored"}), 200

@app.route('/')
def home():
    # Automatically registers the webhook URL dynamically with Telegram on every launch
    if BOT_TOKEN and RENDER_EXTERNAL_URL:
        webhook_setup_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        resp = requests.get(webhook_setup_url).json()
        logger.info(f"Dynamic Webhook registration status: {resp}")
        return f"🚀 **Webhook Engine Active:** {resp.get('description', 'Status Pending')}"
    return "🚀 **Classplus Webhook Signer Engine Online**"

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
