from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ENGINE RECOVERY ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

# Active tracking dictionary for multi-platform sessions
USER_SESSIONS = {}

class UniversalContentSigner:
    def __init__(self, token):
        self.token = token
        self.classplus_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-access-token": self.token,
            "Accept": "application/json",
            "Origin": "https://web.classplusapp.com",
            "Referer": "https://web.classplusapp.com/"
        }
        self.appx_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Authorization": f"Bearer {self.token}" if "Bearer" not in self.token else self.token,
            "Accept": "application/json"
        }

    def sign_classplus(self, raw_url):
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
            
            resp = requests.get(api_endpoint, params=params, headers=self.classplus_headers, timeout=8)
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("status") == "success" and res_json.get("data", {}).get("signedUrl"):
                    return res_json["data"]["signedUrl"]
            
            return f"{clean_base_url}?token={self.token}&user_id=174450341"
        except Exception as e:
            logger.error(f"Classplus signing failure: {e}")
            return raw_url

    def sign_appx(self, raw_url):
        try:
            # Detect standard AppX video streaming structures
            if "appx" not in raw_url and ".m3u8" not in raw_url:
                return raw_url
                
            clean_base_url = raw_url.split('?')[0]
            # Standard AppX dynamic URL token signing pattern
            return f"{clean_base_url}?token={self.token}"
        except Exception as e:
            logger.error(f"AppX signing failure: {e}")
            return raw_url

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=8)
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")

def send_telegram_document(chat_id, file_content, file_name, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        files = {'document': (file_name, file_content, 'text/plain')}
        data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
        requests.post(url, data=data, files=files, timeout=15)
    except Exception as e:
        logger.error(f"Failed to send document: {e}")

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook_catcher():
    update = request.get_json()
    if not update or "message" not in update:
        return jsonify({"status": "ignored"}), 200

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    
    # 1. Command Routing System
    if "text" in message:
        text = message["text"].strip()
        
        if text == "/start":
            USER_SESSIONS[user_id] = {"step": "await_token"}
            send_telegram_message(chat_id, 
                "🚀 **Universal Course Link Signer Engine Loaded**\n\n"
                "Please paste your active access token string below.\n"
                "*(Works for both Classplus `x-access-token` and AppX auth streams!)*"
            )
            return jsonify({"status": "ok"}), 200
            
        elif text == "/reset":
            USER_SESSIONS.pop(user_id, None)
            send_telegram_message(chat_id, "🔄 **Session memory completely cleared!** Type /start to drop a fresh request.")
            return jsonify({"status": "ok"}), 200
            
        elif text == "/help":
            send_telegram_message(chat_id,
                "📖 **Available Extractor Commands:**\n\n"
                "▶️ /start - Initialize a dual-platform extraction sequence\n"
                "🔄 /reset - Clear active token memory allocations\n"
                "ℹ️ /help - Display this command menu"
            )
            return jsonify({"status": "ok"}), 200

        # 2. Dynamic Token Assignment
        if user_id in USER_SESSIONS and USER_SESSIONS[user_id].get("step") == "await_token":
            if len(text) < 30:
                send_telegram_message(chat_id, "❌ That string looks too short to be a valid authentication token. Please send a complete token:")
                return jsonify({"status": "ok"}), 200
                
            USER_SESSIONS[user_id]["token"] = text
            USER_SESSIONS[user_id]["step"] = "await_file"
            send_telegram_message(chat_id,
                "✅ **Token successfully assigned to session matrix!**\n\n"
                "Now, upload your raw dump text file (`.txt`). The scanner will auto-detect Classplus and AppX links concurrently!"
            )
            return jsonify({"status": "ok"}), 200

    # 3. Memory Stream Manifest Parser File Processing Loop
    elif "document" in message:
        if user_id not in USER_SESSIONS or USER_SESSIONS[user_id].get("step") != "await_file":
            send_telegram_message(chat_id, "⚠️ No active extraction session found. Type /start to configure settings first.")
            return jsonify({"status": "ok"}), 200

        document = message["document"]
        file_name = document.get("file_name", "links.txt")
        file_id = document["file_id"]
        
        if not file_name.endswith('.txt'):
            send_telegram_message(chat_id, "❌ Invalid container type. Please send a pure `.txt` manifest text document.")
            return jsonify({"status": "ok"}), 200

        send_telegram_message(chat_id, "📡 *Downloading manifest file stream into server memory buffer...*")
        
        try:
            get_file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
            file_info = requests.get(get_file_url, timeout=8).json()
            
            if file_info.get("ok"):
                file_path = file_info["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                
                raw_content = requests.get(download_url, timeout=10).text
                user_token = USER_SESSIONS[user_id]["token"]
                signer = UniversalContentSigner(user_token)
                
                processed_lines = []
                classplus_count = 0
                appx_count = 0
                
                for line in raw_content.splitlines():
                    if "http" in line:
                        prefix, actual_url = line.split("http", 1)
                        actual_url = "http" + actual_url.strip()
                        
                        # Automated routing based on link signatures
                        if "classplus" in actual_url or "unacademy" in actual_url or "master.m3u8" in actual_url or "playlist.m3u8" in actual_url:
                            signed_link = signer.sign_classplus(actual_url)
                            classplus_count += 1
                        elif "appx" in actual_url or "media-cdn" in actual_url:
                            signed_link = signer.sign_appx(actual_url)
                            appx_count += 1
                        else:
                            signed_link = actual_url  # Leaves external URLs untouched
                            
                        processed_lines.append(f"{prefix.strip()} {signed_link}")
                    else:
                        processed_lines.append(line)
                
                output_content = "\n".join(processed_lines)
                output_filename = f"signed_{file_name}"
                
                stats_summary = f"✅ **Dual Extraction Strategy Complete!**\n\n🔹 Classplus Links Signed: `{classplus_count}`\n🔸 AppX Links Signed: `{appx_count}`\n\n*Session closed. Use /start for a new batch execution.*"
                
                send_telegram_document(chat_id, output_content, output_filename, stats_summary)
                USER_SESSIONS.pop(user_id, None)
            else:
                send_telegram_message(chat_id, "⚠️ Failed to fetch download coordinates from Telegram storage grid.")
        except Exception as e:
            logger.error(f"Error executing dual signing sequence: {e}")
            send_telegram_message(chat_id, f"⚠️ **Processing layout dropped error exception:** `{str(e)}`")
            
        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "ignored"}), 200

@app.route('/')
def home():
    if BOT_TOKEN and RENDER_EXTERNAL_URL:
        webhook_setup_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        resp = requests.get(webhook_setup_url).json()
        return f"🚀 **Universal Webhook Engine Active:** {resp.get('description', 'Status Pending')}"
    return "🚀 **Universal Webhook Signer Engine Online**"

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
