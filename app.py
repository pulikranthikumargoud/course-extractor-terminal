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

USER_SESSIONS = {}

ADMIN_USERNAME = "@kranthikumar_goud"
ADMIN_ID = "1001653060"
BRAND_NAME = "@kranthikumargoudEEE"

# Production-Grade Multi-Tenant Headers for ClassX Infrastructure
CLASSX_CLIENT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://www.ohminstitute.live",
    "Referer": "https://www.ohminstitute.live/"
}

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
            [{"text": "⚡ 2. AppX / ClassX Engine", "callback_data": "menu_appx"}],
            [{"text": "🔒 3. Text to Video Extract (Premium)", "callback_data": "menu_extract"}]
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

def get_back_button():
    return {"inline_keyboard": [[{"text": "⬅️ Back to Main Menu", "callback_data": "go_main"}]]}

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

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        if "text" in message:
            text = message["text"].strip()
            
            if text == "/start" or text == "/reset":
                USER_SESSIONS[user_id] = {"step": "idle", "platform": None, "token": None, "api_base": ""}
                send_msg(chat_id, f"🚀 **Welcome to {BRAND_NAME} Extractor Engine**\n\nSelect your operation path layer below to begin:", reply_markup=get_main_menu())
                return jsonify({"status": "ok"}), 200

            state = USER_SESSIONS.get(user_id, {}).get("step", "idle")
            
            # --- REAL CLASSPLUS INTERACTION STEP ---
            if state == "cp_await_org_num":
                if "*" not in text:
                    send_msg(chat_id, "❌ Invalid format. Use `ORGCODE*MOBILE` (e.g., `gxsrt*9949xxxxxx`):")
                    return jsonify({"status": "ok"}), 200
                org, phone = text.split("*", 1)
                USER_SESSIONS[user_id].update({"step": "cp_await_otp", "org": org.strip().lower(), "phone": phone.strip()})
                
                try:
                    cp_url = f"https://api.classplusapp.com/v2/users/otp?mobileNumber={phone.strip()}&orgCode={org.strip().lower()}"
                    requests.get(cp_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                except Exception:
                    pass

                send_msg(chat_id, f"📡 *Request sent to Classplus infrastructure!* Verification code requested for **{phone.strip()}**.\n\nEnter your **4-Digit OTP**:")
                return jsonify({"status": "ok"}), 200

            elif state == "cp_await_otp":
                session = USER_SESSIONS[user_id]
                try:
                    verify_url = "https://api.classplusapp.com/v2/users/verify"
                    payload = {"mobileNumber": session["phone"], "orgCode": session["org"], "otp": text.strip()}
                    resp = requests.post(verify_url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=8).json()
                    
                    if resp.get("status") == "success" or "data" in resp:
                        token = resp["data"]["token"]
                        USER_SESSIONS[user_id].update({"step": "await_file", "platform": "classplus", "token": token})
                        send_msg(chat_id, f"✅ **Classplus Login Successful!**\n\nNow, upload your link dump text file (`.txt`):")
                    else:
                        send_msg(chat_id, f"❌ **Verification Failed:** `{resp.get('message', 'Invalid OTP verification code')}`")
                except Exception as e:
                    send_msg(chat_id, f"⚠️ Connection Error: `{str(e)}`")
                return jsonify({"status": "ok"}), 200

            elif state == "cp_await_direct_token":
                USER_SESSIONS[user_id].update({"step": "await_file", "platform": "classplus", "token": text})
                send_msg(chat_id, "✅ **Classplus token locked successfully!**\n\nNow, upload your raw link dump text file (`.txt`) container:")
                return jsonify({"status": "ok"}), 200

            # --- DYNAMIC APPX & CLASSX CLUSTER LAYER ---
            elif state == "appx_await_base_url":
                input_url = text.lower()
                # Dynamically match dedicated API domains like classx.co.in or fallback to sub-domains
                if "ohminstitute" in input_url:
                    api_base = "https://eeecliveapi.classx.co.in/api/v1"
                else:
                    clean_domain = input_url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                    api_base = f"https://api.{clean_domain}/api/v1"

                USER_SESSIONS[user_id].update({"step": "appx_choose_login_method", "api_base": api_base})
                send_msg(chat_id, f"🌐 **Validated Cluster API Endpoint:**\n`{api_base}`\n\nSelect your connection format:", reply_markup=get_appx_submenu())
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_creds_pass":
                if "*" not in text:
                    send_msg(chat_id, "❌ Invalid format. Please use `MOBILE*PASSWORD`:")
                    return jsonify({"status": "ok"}), 200
                phone, password = text.split("*", 1)
                session = USER_SESSIONS[user_id]
                
                try:
                    login_url = f"{session['api_base']}/auth/v2/login"
                    payload = {"phone": phone.strip(), "password": password.strip()}
                    resp = requests.post(login_url, json=payload, headers=CLASSX_CLIENT_HEADERS, timeout=8).json()
                    
                    if resp.get("success") or "token" in resp:
                        token = resp.get("token") or resp.get("data", {}).get("token")
                        USER_SESSIONS[user_id].update({"step": "await_file", "platform": "appx", "token": token})
                        send_msg(chat_id, f"✅ **Handshake Success! Profile Unlocked.**\n\nNow, upload your link dump text file (`.txt`):")
                    else:
                        send_msg(chat_id, f"❌ **Authentication Rejected:** `{resp.get('message', 'Invalid login credentials')}`")
                except Exception as e:
                    send_msg(chat_id, f"⚠️ Endpoint Connection Error: `{str(e)}`")
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_num_otp":
                session = USER_SESSIONS[user_id]
                phone_num = text.strip()
                USER_SESSIONS[user_id].update({"step": "appx_await_otp_verify", "phone": phone_num})
                
                try:
                    otp_url = f"{session['api_base']}/auth/v2/send-otp"
                    payload = {"phone": phone_num}
                    requests.post(otp_url, json=payload, headers=CLASSX_CLIENT_HEADERS, timeout=8)
                except Exception:
                    pass
                    
                send_msg(chat_id, f"📡 OTP request broadcasted to **{phone_num}** via cluster gateway.\n\nEnter the **6-Digit OTP** login validation key:")
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_otp_verify":
                session = USER_SESSIONS[user_id]
                try:
                    verify_url = f"{session['api_base']}/auth/v2/verify-otp"
                    payload = {"phone": session["phone"], "otp": text.strip()}
                    resp = requests.post(verify_url, json=payload, headers=CLASSX_CLIENT_HEADERS, timeout=8).json()
                    
                    if resp.get("success") or "token" in resp:
                        token = resp.get("token") or resp.get("data", {}).get("token")
                        USER_SESSIONS[user_id].update({"step": "await_file", "platform": "appx", "token": token})
                        send_msg(chat_id, f"✅ **Verification Code Accepted! Secure context allocated.**\n\nNow, upload your link dump text file (`.txt`):")
                    else:
                        send_msg(chat_id, f"❌ **Invalid OTP Code:** `{resp.get('message', 'The code entered is incorrect')}`. Use /start to reset.")
                except Exception as e:
                    send_msg(chat_id, f"⚠️ Cluster Network Exception: `{str(e)}`")
                return jsonify({"status": "ok"}), 200

            elif state == "appx_await_direct_token":
                USER_SESSIONS[user_id].update({"step": "await_file", "platform": "appx", "token": text})
                send_msg(chat_id, "✅ **AppX / ClassX Bearer Token saved!**\n\nNow, upload your raw link dump text file (`.txt`):")
                return jsonify({"status": "ok"}), 200

        # --- TEXT FILE LINK PROCESSING LOOP ---
        elif "document" in message:
            if USER_SESSIONS.get(user_id, {}).get("step") != "await_file":
                send_msg(chat_id, "⚠️ No active token configuration locked for this profile. Type /start to load settings.")
                return jsonify({"status": "ok"}), 200

            document = message["document"]
            file_name = document.get("file_name", "links.txt")
            if not file_name.endswith('.txt'):
                send_msg(chat_id, "❌ File type mismatch. Please upload a structured `.txt` document file.")
                return jsonify({"status": "ok"}), 200

            send_msg(chat_id, "📡 *Downloading file container stream directly into memory...*")
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
                send_doc(chat_id, output_text, f"signed_{file_name}", f"✅ **Extraction Completed Successfully!**\n\n⚙️ Platform: `{session_data['platform'].upper()}`\n🔗 Links Remapped: `{count}`\n\n*Session closed. Use /start to run a new batch.*")
                USER_SESSIONS.pop(user_id, None)
            except Exception as e:
                send_msg(chat_id, f"⚠️ **Processing engine exception:** `{str(e)}`")
            return jsonify({"status": "ok"}), 200

    elif "callback_query" in update:
        query = update["callback_query"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        user_id = query["from"]["id"]
        data = query["data"]

        if user_id not in USER_SESSIONS:
            USER_SESSIONS[user_id] = {"step": "idle", "platform": None, "token": None, "api_base": ""}

        if data == "go_main":
            edit_msg(chat_id, message_id, f"🚀 **Welcome to {BRAND_NAME} Extractor Engine**\n\nSelect your operation path layer below to begin:", reply_markup=get_main_menu())
        elif data == "menu_cp":
            edit_msg(chat_id, message_id, "🛡️ **Classplus Engine Configuration Setup**\n\nChoose an option to authenticate your extraction container run:", reply_markup=get_classplus_submenu())
        elif data == "cp_otp_init":
            USER_SESSIONS[user_id]["step"] = "cp_await_org_num"
            send_msg(chat_id, "📱 **Classplus Automated OTP Login Mode**\n\nPlease submit your details exactly in this format:\n`ORGCODE*MOBILE_NUMBER`\n\n*(Example: `gxsrt*9949xxxxxx`)*")
        elif data == "cp_direct_token":
            USER_SESSIONS[user_id]["step"] = "cp_await_direct_token"
            send_msg(chat_id, "🔑 **Classplus Token Manual Ingestion**\n\nPlease paste your raw `x-access-token` string copied directly from your browser dev tools:")
        elif data == "menu_appx":
            USER_SESSIONS[user_id]["step"] = "appx_await_base_url"
            send_msg(chat_id, "⚡ **AppX / ClassX Link Strategy Initializer**\n\nPlease paste your portal website or application base URL address first:\n\n*(Example: `https://www.ohminstitute.live/` or `https://delhiiasprep.com`)*")
        elif data == "appx_pass_init":
            USER_SESSIONS[user_id]["step"] = "appx_await_creds_pass"
            send_msg(chat_id, "🔐 **AppX / ClassX Credential Validation Strategy**\n\nPlease pass parameters exactly as:\n`MOBILE_NUMBER*PASSWORD`\n\n*(Example: `9876543210*MySecurePass123`)*")
        elif data == "appx_otp_init":
            USER_SESSIONS[user_id]["step"] = "appx_await_num_otp"
            send_msg(chat_id, "📱 **AppX / ClassX API OTP Verification Mode**\n\nPlease type your registered **10-Digit Mobile Number** to request a dynamic sign-in token:")
        elif data == "appx_direct_token":
            USER_SESSIONS[user_id]["step"] = "appx_await_direct_token"
            send_msg(chat_id, "🔑 **AppX / ClassX Bearer Token Manual Ingestion**\n\nPlease paste your complete authorization token text string value directly here:")
        elif data == "menu_extract":
            paywall_text = (
                f"⚠️ **Access Denied — Subscription Required** ⚠️\n\n"
                f"The **Text to Video Extract** workflow feature is exclusively locked for premium VIP plan members under the {BRAND_NAME} brand framework.\n\n"
                f"To verify your profile workspace node and purchase a premium license token, please message the owner immediately with your connection data details below:\n\n"
                f"👤 **Owner Username:** {ADMIN_USERNAME}\n"
                f"🆔 **Admin Profile ID:** `{ADMIN_ID}`\n"
                f"👑 **Owner Legal Name:** Kranthikumar Goud\n"
                f"🌐 **Language Context:** English (`en`)\n\n"
                f"👉 Tap the button below to return to the baseline configuration options menu."
            )
            edit_msg(chat_id, message_id, paywall_text, reply_markup=get_back_button())

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
