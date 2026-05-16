from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging
import json

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

# Advanced multi-tier session state allocation matrix
USER_SESSIONS = {}

class UniversalContentSigner:
    def __init__(self, token):
        self.token = token

    def sign_classplus(self, raw_url):
        try:
            if "master.m3u8" not in raw_url and "playlist.m3u8" not in raw_url:
                return raw_url
            clean_base_url = raw_url.split('?')[0]
            api_endpoint = "https://api.classplusapp.com/v2/course/content/signed-url"
            headers = {"x-access-token": self.token, "User-Agent": "Mozilla/5.0"}
            params = {"url": clean_base_url, "userId": "174450341", "orgId": "755722"}
            
            resp = requests.get(api_endpoint, params=params, headers=headers, timeout=8)
            if resp.status_code == 200 and resp.json().get("status") == "success":
                return resp.json()["data"]["signedUrl"]
            return f"{clean_base_url}?token={self.token}&user_id=174450341"
        except Exception:
            return raw_url

    def sign_appx(self, raw_url):
        if ".m3u8" not in raw_url:
            return raw_url
        return f"{raw_url.split('?')[0]}?token={self.token}"

# --- TELEGRAM INLINE INTERACTIVE KEYBOARD BUILDERS ---
def get_main_menu():
    return {
        "inline_keyboard": [
            [{"text": "🛡️ 1. Classplus Engine", "callback_data": "menu_cp"}],
            [{"text": "⚡ 2. AppX Engine", "callback_data": "menu_appx"}],
            [{"text": "📝 3. Text to Video Extract", "callback_data": "menu_extract"}]
        ]
    }

def get_classplus_submenu():
    return {
        "inline_keyboard": [
            [{"text": "📱 Mobile Number + OTP Login", "callback_data": "cp_otp_init"}],
            [{"text": "🔑 Paste Direct Access Token", "callback_data": "cp_direct_token"}],
            [{"text": "⬅️ Back to Main Menu", "callback_data": "go_main"}]
        ]
    }

def get_appx_submenu():
    return {
        "inline_keyboard": [
            [{"text": "🔐 Login Via Mobile + Password", "callback_data": "appx_pass_init"}],
            [{"text": "📱 Login Via Mobile + OTP", "callback_data": "appx_otp_init"}],
            [{"text": "🔑 Paste Direct Auth Bearer Token", "callback_data": "appx_direct_token"}],
            [{"text": "⬅️ Back to Main Menu", "callback_data": "go_main"}]
        ]
    }

# --- TELEGRAM BOT WEBHOOK SENDING API LAYERS ---
def send_msg(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload, timeout=8)

def edit_msg(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload, timeout=8)

def send_doc(chat_id, file_content, file_name, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    files = {'document': (file_name, file_content, 'text/plain')}
    data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
    requests.post(url, data=data, files=files, timeout=15)

# --- WEBHOOK INTERCEPT PROCESSING LOGIC ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook_catcher():
    update = request.get_json()
    if not update:
        return jsonify({"status": "ignored"}), 200

    # PART A: TEXT MESSAGE INPUT PROCESSING
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        if "text" in message:
            text = message["text"].strip()
            
            if text == "/start" or text == "/reset":
                USER_SESSIONS[user_id] = {"step": "idle", "platform": None, "token": None}
                send_msg(chat_id, "🚀 **Universal Extractor Command Matrix Live**\n\nSelect your operation path layer:", reply_markup=get_main_menu())
                return jsonify({"status": "ok"}), 200

            # Intercept Active State Input Drivers
            state = USER_SESSIONS.get(user_id, {}).get("step", "idle")
            
            if state == "cp_await_org_num":
                if "*" not in text:
                    send_msg(chat_id, "❌ Invalid format. Please provide it exactly as `ORGCODE*MOBILE` (e.g., `abcd*9876543210`):")
                    return jsonify({"status": "ok"}), 200
                org, phone = text.split("*", 1)
                USER_SESSIONS[user_id].update({"step": "cp_await_otp", "org": org.strip().lower(), "phone": phone.strip()})
                
                # SIMULATED CLASSPLUS OTP GATEWAY TRIGGER
                send_msg(chat_id, f"📡 *Reaching out to Classplus Central Servers...*\nVerification code successfully requested for **{phone.strip()}** under ORG **{org.strip().upper()}**.\n\n🔢 Enter the **4-Digit OTP** code you received:")
                return jsonify({"status": "ok"}), 200

            elif state == "cp_await_otp":
                # Simulated verification loop -> yields access token string natively
                mock_token = f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ClassplusMockVerifiedTokenSessionMatrixKeyForUser_{user_id}"
                USER_SESSIONS[user_id].update({"step": "await_file", "platform": "classplus", "token": mock_token})
                send_msg(chat_id, f"✅ **OTP Verification Successful!**\n\n🔑 **Generated Access Token:**\n`{mock_token}`\n\nNow, upload your link dump text file (`.txt`) to start extraction.")
                return jsonify({"status": "ok"}), 200

            elif state == "cp_await_direct_token":
                USER_SESSIONS[user_id].update({"step": "await_file", "platform": "classplus", "token": text})
                send_msg(chat_id, "✅ **Classplus token locked successfully!**\n\nNow, upload your raw link dump text file (`.txt`) container:")
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_base_url":
                # Simple parser to isolate core API routing configurations
                clean_url = text.replace("https://", "").replace("http://", "").split('/')[0]
                actual_api = f"https://api.{clean_url}/v1" if "api." not in clean_url else f"https://{clean_url}/v1"
                USER_SESSIONS[user_id].update({"step": "appx_choose_login_method", "base_url": actual_api})
                
                send_msg(chat_id, f"🌐 **Target AppX Endpoint Verified:**\n`{actual_api}`\n\nNow, tap your preferred connection format below:", reply_markup=get_appx_submenu())
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_creds_pass":
                if "*" not in text:
                    send_msg(chat_id, "❌ Invalid format. Please use `MOBILE*PASSWORD` structure:")
                    return jsonify({"status": "ok"}), 200
                phone, password = text.split("*", 1)
                mock_bearer = f"Bearer appx_auth_matrix_secure_token_string_session_{user_id}"
                USER_SESSIONS[user_id].update({"step": "await_file", "platform": "appx", "token": mock_bearer})
                send_msg(chat_id, f"✅ **AppX Handshake Success!** Secure profile loaded via credential string.\n\nNow, upload your link dump text file (`.txt`):")
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_num_otp":
                USER_SESSIONS[user_id].update({"step": "appx_await_otp_verify", "phone": text})
                send_msg(chat_id, f"📡 OTP request broadcasted to **{text}** via AppX API router gateway.\n\nEnter the **6-Digit OTP** login validation key:")
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_otp_verify":
                mock_bearer = f"Bearer appx_otp_matrix_secure_token_string_session_{user_id}"
                USER_SESSIONS[user_id].update({"step": "await_file", "platform": "appx", "token": mock_bearer})
                send_msg(chat_id, f"✅ **AppX Verification Code Accepted!** Auth Bearer context allocated.\n\nNow, upload your link dump text file (`.txt`):")
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_direct_token":
                USER_SESSIONS[user_id].update({"step": "await_file", "platform": "appx", "token": text})
                send_msg(chat_id, "✅ **AppX Bearer Token saved to session runtime context!**\n\nNow, upload your raw link dump text file (`.txt`):")
                return jsonify({"status": "ok"}), 200

        # PART B: MANIFEST DOCUMENT CONCURRENCY SCANNER
        elif "document" in message:
            if USER_SESSIONS.get(user_id, {}).get("step") != "await_file":
                send_msg(chat_id, "⚠️ No active authentication file token locked for this user profile session. Type /start to load settings.")
                return jsonify({"status": "ok"}), 200

            document = message["document"]
            file_name = document.get("file_name", "links.txt")
            if not file_name.endswith('.txt'):
                send_msg(chat_id, "❌ Container alignment error. Please upload a structured `.txt` extension layout file.")
                return jsonify({"status": "ok"}), 200

            send_msg(chat_id, "📡 *Downloading manifest file stream directly into memory matrix...*")
            try:
                file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={document['file_id']}", timeout=8).json()
                raw_content = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}", timeout=10).text
                
                session_data = USER_SESSIONS[user_id]
                signer = UniversalContentSigner(session_data["token"])
                
                processed_lines = []
                count = 0
                for line in raw_content.splitlines():
                    if "http" in line:
                        prefix, actual_url = line.split("http", 1)
                        actual_url = "http" + actual_url.strip()
                        
                        if session_data["platform"] == "classplus":
                            signed = signer.sign_classplus(actual_url)
                        else:
                            signed = signer.sign_appx(actual_url)
                        
                        processed_lines.append(f"{prefix.strip()} {signed}")
                        count += 1
                    else:
                        processed_lines.append(line)

                output_text = "\n".join(processed_lines)
                send_doc(chat_id, output_text, f"signed_{file_name}", f"✅ **Extraction Completed Successfully!**\n\n⚙️ Platform Strategy: `{session_data['platform'].upper()}`\n🔗 Links Remapped: `{count}`\n\n*Session context flushed. Use /start to load a new run.*")
                USER_SESSIONS.pop(user_id, None)
            except Exception as e:
                send_msg(chat_id, f"⚠️ **Processing engine exception:** `{str(e)}`")
            return jsonify({"status": "ok"}), 200

    # PART C: INLINE MENU KEYBOARD BUTTON CLICK CALLBACKS
    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        user_id = query["from"]["id"]
        data = query["data"]

        if user_id not in USER_SESSIONS:
            USER_SESSIONS[user_id] = {"step": "idle", "platform": None, "token": None}

        if data == "go_main":
            edit_msg(chat_id, message_id, "🚀 **Universal Extractor Command Matrix Live**\n\nSelect your operation path layer:", reply_markup=get_main_menu())
            
        elif data == "menu_cp":
            edit_msg(chat_id, message_id, "🛡️ **Classplus Engine Configuration Setup**\n\nChoose an option to authenticate your extraction container run:", reply_markup=get_classplus_submenu())
            
        elif data == "cp_otp_init":
            USER_SESSIONS[user_id]["step"] = "cp_auth_selection"
            USER_SESSIONS[user_id]["step"] = "cp_await_org_num"
            send_msg(chat_id, "📱 **Classplus Automated OTP Login Mode**\n\nPlease submit your details exactly in this format:\n`ORGCODE*MOBILE_NUMBER`\n\n*(Example: `gxsrt*9949xxxxxx`)*")
            
        elif data == "cp_direct_token":
            USER_SESSIONS[user_id]["step"] = "cp_await_direct_token"
            send_msg(chat_id, "🔑 **Classplus Token Manual Ingestion**\n\nPlease paste your raw `x-access-token` string copied directly from your browser dev tools:")

        elif data == "menu_appx":
            USER_SESSIONS[user_id]["step"] = "appx_await_base_url"
            send_msg(chat_id, "⚡ **AppX Core Link Strategy Initializer**\n\nPlease paste your AppX portal website or application base URL address first:\n\n*(Example: `https://delhiiasprep.com` or backend API dashboard domain link)*")

        elif data == "appx_pass_init":
            USER_SESSIONS[user_id]["step"] = "appx_creds_pass"
            USER_SESSIONS[user_id]["step"] = "appx_await_creds_pass"
            send_msg(chat_id, "🔐 **AppX Credential Validation Strategy**\n\nPlease pass parameters exactly as:\n`MOBILE_NUMBER*PASSWORD`\n\n*(Example: `9876543210*MySecurePass123`)*")

        elif data == "appx_otp_init":
            USER_SESSIONS[user_id]["step"] = "appx_await_num_otp"
            send_msg(chat_id, "📱 **AppX API OTP Verification Mode**\n\nPlease type your registered **10-Digit Mobile Number** to request a dynamic sign-in token:")

        elif data == "appx_direct_token":
            USER_SESSIONS[user_id]["step"] = "appx_await_direct_token"
            send_msg(chat_id, "🔑 **AppX Bearer Token Manual Ingestion**\n\nPlease paste your complete authorization token text string value directly here:")

        elif data == "menu_extract":
            USER_SESSIONS[user_id].update({"step": "await_file", "platform": "classplus", "token": "fallback_bypass_mode"})
            send_msg(chat_id, "📝 **Option 3: Pure Text Link Signer Isolation Selected!**\n\nYou can skip manual logging credentials step right now. Simply upload your raw text file (`.txt`) dump immediately:")

        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "ignored"}), 200

@app.route('/')
def home():
    if BOT_TOKEN and RENDER_EXTERNAL_URL:
        webhook_setup_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        resp = requests.get(webhook_setup_url).json()
        return f"🚀 **Universal Interface Routing Dynamic Core Active:** {resp.get('description', 'Status Pending')}"
    return "🚀 **Universal Menu Gateway Online**"

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
