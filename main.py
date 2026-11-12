# المصدر الأصلي: الذئب الأبيض (@j49_c)
# إدارة وحقوق تخصيص النسخة: @ASADALY1 | قناة المشروع: @hadZv1
import telebot
import json
import threading
import time
import random
import string
import re
import requests
import zipfile
import hashlib
import base64
import os
import sys
import subprocess
from telebot import types, apihelper
from datetime import datetime, timedelta
from html import escape
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# ===== إعدادات الاتصال المحسنة للسرعة =====
apihelper.READ_TIMEOUT = 30
apihelper.CONNECT_TIMEOUT = 30

# ===== التوكنات =====
TOKEN = os.getenv("BOT_TOKEN", "9183977130:AAHlLpwylSEC5sO-Q2Dc2eusU1YjT0plZ-8").strip()
ADMIN_ID = 8664763495
OWNER_URL = "https://t.me/ASADALY1"
CHANNEL_URL = "https://t.me/hadZv1"
PROJECT_RIGHTS = "© جميع الحقوق محفوظة — إدارة وتطوير: @ASADALY1"
HIDDEN_LONG = "ㅤ" * 50

# ===== إنشاء البوت =====
if not TOKEN:
    raise RuntimeError("BOT_TOKEN غير مضبوط. أضف التوكن الجديد في متغيرات البيئة باسم BOT_TOKEN.")

try:
    bot = telebot.TeleBot(TOKEN, threaded=True, parse_mode="HTML")
    bot.get_me()
    print("✅ البوت متصل بنجاح!")
except Exception as e:
    print(f"❌ فشل الاتصال: {e}")
    bot = telebot.TeleBot(TOKEN, threaded=True, parse_mode="HTML")

# ===== المجلدات =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNNING_DIR = os.path.join(BASE_DIR, 'active_bots')
LOGS_DIR = os.path.join(BASE_DIR, 'bot_logs')
DB_DIR = os.path.join(BASE_DIR, 'database')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
STORE_DIR = os.path.join(BASE_DIR, 'store_files')
THUMBS_DIR = os.path.join(ASSETS_DIR, 'thumbs')
MARKET_DIR = os.path.join(BASE_DIR, 'market')
ENV_DIR = os.path.join(BASE_DIR, 'bot_environments')
ENCRYPTED_DIR = os.path.join(BASE_DIR, 'encrypted_files')

for d in [RUNNING_DIR, LOGS_DIR, DB_DIR, ASSETS_DIR, STORE_DIR, THUMBS_DIR, MARKET_DIR, ENV_DIR, ENCRYPTED_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# ===== قواعد البيانات =====
USERS_DB = os.path.join(DB_DIR, 'users.json')
FILES_DB = os.path.join(DB_DIR, 'files.json')
SETTINGS_DB = os.path.join(DB_DIR, 'settings.json')
STORE_DB = os.path.join(DB_DIR, 'store.json')
ADMINS_DB = os.path.join(DB_DIR, 'admins.json')
MARKET_DB = os.path.join(DB_DIR, 'market.json')
SECURITY_DB = os.path.join(DB_DIR, 'security.json')

db_lock = threading.Lock()
cancel_states = {}
last_bot_messages = {}
active_processes = {}
process_hours = {}
user_notifications = {}

def read_json(path):
    with db_lock:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except:
            return {}

def write_json(path, data):
    with db_lock:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except:
            pass

def init_db():
    default_settings = {
        "channels": [],
        "bot_name": "ASAD HOSTING",
        "bot_image": None,
        "file_thumb": None,
        "bot_locked": False,
        "auto_approve": False
    }
    current_settings = read_json(SETTINGS_DB)
    for key, value in default_settings.items():
        if key not in current_settings:
            current_settings[key] = value
    write_json(SETTINGS_DB, current_settings)
    
    for path in [USERS_DB, FILES_DB, STORE_DB, MARKET_DB, SECURITY_DB]:
        if not os.path.exists(path):
            write_json(path, {})
    
    if not os.path.exists(ADMINS_DB):
        write_json(ADMINS_DB, {"admins": [ADMIN_ID]})
    else:
        admins_data = read_json(ADMINS_DB)
        if ADMIN_ID not in admins_data.get("admins", []):
            admins_data["admins"] = admins_data.get("admins", []) + [ADMIN_ID]
            write_json(ADMINS_DB, admins_data)
    
    for uid in user_notifications:
        user_notifications[uid] = True
    
    init_security()

def init_security():
    security = read_json(SECURITY_DB)
    if 'master_key' not in security:
        master_key = base64.b64encode(get_random_bytes(32)).decode('utf-8')
        security['master_key'] = master_key
        security['file_keys'] = {}
        write_json(SECURITY_DB, security)

def get_master_key():
    security = read_json(SECURITY_DB)
    master_key = security.get('master_key')
    if not master_key:
        master_key = base64.b64encode(get_random_bytes(32)).decode('utf-8')
        security['master_key'] = master_key
        write_json(SECURITY_DB, security)
    return base64.b64decode(master_key)

def generate_file_key(fid, user_id):
    security = read_json(SECURITY_DB)
    file_keys = security.get('file_keys', {})
    
    if fid not in file_keys:
        combined = f"{fid}:{user_id}:{ADMIN_ID}:{TOKEN}"
        salt = hashlib.sha256(combined.encode()).digest()[:16]
        
        master_key = get_master_key()
        kdf = hashlib.pbkdf2_hmac('sha256', master_key, salt, 100000, dklen=32)
        
        file_keys[fid] = {
            'key': base64.b64encode(kdf).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
            'user_id': user_id
        }
        security['file_keys'] = file_keys
        write_json(SECURITY_DB, security)
    
    return file_keys[fid]

def get_file_key(fid):
    security = read_json(SECURITY_DB)
    file_keys = security.get('file_keys', {})
    return file_keys.get(fid)

def encrypt_file_content(content, fid, user_id):
    try:
        file_key_info = generate_file_key(fid, user_id)
        key = base64.b64decode(file_key_info['key'])
        salt = base64.b64decode(file_key_info['salt'])
        
        cipher = AES.new(key, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(content.encode('utf-8'), AES.block_size))
        
        encrypted_data = {
            'iv': base64.b64encode(cipher.iv).decode('utf-8'),
            'ciphertext': base64.b64encode(ct_bytes).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
            'fid': fid,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        return json.dumps(encrypted_data)
    except Exception as e:
        print(f"Encryption error: {e}")
        return None

def decrypt_file_content(encrypted_json, fid):
    try:
        data = json.loads(encrypted_json)
        
        file_key_info = get_file_key(fid)
        if not file_key_info:
            return None
        
        key = base64.b64decode(file_key_info['key'])
        iv = base64.b64decode(data['iv'])
        ct = base64.b64decode(data['ciphertext'])
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        
        return pt.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def save_encrypted_file(fid, content, user_id):
    encrypted_content = encrypt_file_content(content, fid, user_id)
    if encrypted_content:
        encrypted_path = os.path.join(ENCRYPTED_DIR, f"{fid}.enc")
        with open(encrypted_path, 'w', encoding='utf-8') as f:
            f.write(encrypted_content)
        return True
    return False

def load_encrypted_file(fid):
    encrypted_path = os.path.join(ENCRYPTED_DIR, f"{fid}.enc")
    if os.path.exists(encrypted_path):
        with open(encrypted_path, 'r', encoding='utf-8') as f:
            encrypted_content = f.read()
        return decrypt_file_content(encrypted_content, fid)
    return None

def save_running_file(fid, content):
    running_path = os.path.join(RUNNING_DIR, f"{fid}.py")
    with open(running_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return running_path

def verify_file_access(fid, user_id):
    files = read_json(FILES_DB)
    if fid not in files:
        return False
    
    file_info = files[fid]
    file_user_id = file_info.get('user_id')
    
    if user_id == ADMIN_ID or is_admin(user_id):
        return True
    
    if file_user_id == user_id:
        return True
    
    if file_info.get('type') == 'store':
        store = read_json(STORE_DB)
        if fid in store:
            return True
    
    return False

def get_settings():
    return read_json(SETTINGS_DB)

def save_settings(settings):
    write_json(SETTINGS_DB, settings)

def is_bot_locked():
    return get_settings().get('bot_locked', False)

def toggle_bot_lock():
    settings = get_settings()
    settings['bot_locked'] = not settings.get('bot_locked', False)
    save_settings(settings)
    return settings['bot_locked']

def toggle_auto_approve():
    settings = get_settings()
    settings['auto_approve'] = not settings.get('auto_approve', True)
    save_settings(settings)
    return settings['auto_approve']

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    admins_data = read_json(ADMINS_DB)
    return user_id in admins_data.get("admins", [])

def is_main_admin(user_id):
    return user_id == ADMIN_ID

def get_admins():
    admins_data = read_json(ADMINS_DB)
    return admins_data.get("admins", [ADMIN_ID])

def add_admin(user_id):
    admins_data = read_json(ADMINS_DB)
    if user_id not in admins_data.get("admins", []):
        admins_data["admins"] = admins_data.get("admins", []) + [user_id]
        write_json(ADMINS_DB, admins_data)
        return True
    return False

def remove_admin(user_id):
    if user_id == ADMIN_ID:
        return False
    admins_data = read_json(ADMINS_DB)
    if user_id in admins_data.get("admins", []):
        admins_data["admins"].remove(user_id)
        write_json(ADMINS_DB, admins_data)
        return True
    return False

# ===== تنسيق رسائل البوت وإظهار حقوق المشروع =====
def deco(title, content):
    return f"{content}\n\n{HIDDEN_LONG}"

def delete_last_message(chat_id):
    # تم تعطيل حذف الرسائل القديمة
    pass

def save_message(chat_id, msg_id):
    last_bot_messages[chat_id] = msg_id

def apply_project_rights(text):
    text = str(text)
    if PROJECT_RIGHTS not in text:
        text = f"{text}\n\n{PROJECT_RIGHTS}"
    return text

def send_msg(chat_id, text, markup=None):
    text = apply_project_rights(text)
    settings = get_settings()
    try:
        if settings.get('bot_image'):
            msg = bot.send_photo(chat_id, settings['bot_image'], caption=text, parse_mode="HTML", reply_markup=markup)
        else:
            msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
        save_message(chat_id, msg.message_id)
        return msg
    except:
        msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
        save_message(chat_id, msg.message_id)
        return msg

def edit_msg(call, text, markup):
    text = apply_project_rights(text)
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(text[:4096], call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        else:
            bot.edit_message_text(text[:4096], call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        save_message(call.message.chat.id, call.message.message_id)
    except:
        pass

def del_msg(chat_id, *msg_ids):
    for msg_id in msg_ids:
        if msg_id:
            try:
                bot.delete_message(chat_id, msg_id)
            except:
                pass

def is_user_pro(uid):
    if uid == ADMIN_ID or is_admin(uid):
        return True
    users = read_json(USERS_DB)
    u = users.get(str(uid), {})
    expiry = u.get('expiry')
    if not expiry or expiry == 'null':
        return False
    if expiry == 'LIFETIME' or expiry == 0:
        return True
    try:
        exp_date = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < exp_date:
            return True
        else:
            u['expiry'] = None
            users[str(uid)] = u
            write_json(USERS_DB, users)
            return False
    except:
        return False

def check_sub(user_id):
    if user_id == ADMIN_ID or is_admin(user_id):
        return True
    settings = get_settings()
    channels = settings.get('channels', [])
    if not channels:
        return True
    try:
        for ch in channels:
            member = bot.get_chat_member(ch["username"], user_id)
            if member.status in ['left', 'kicked']:
                return False
        return True
    except Exception as e:
        print(f"Subscription check error: {e}")
        return False

def get_preview(path, lines=40):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.readlines()
                preview = "".join(content[:lines])
                safe = escape(preview)
                if len(safe) > 3000:
                    safe = safe[:3000] + "\n..."
                return f"<pre><code class='language-python'>{safe}</code></pre>"
        return "تعذر قراءة الملف"
    except:
        return "خطأ في القراءة"

def get_logs(fid, lines=40):
    log_path = os.path.join(LOGS_DIR, f"{fid}.log")
    try:
        if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                last = all_lines[-lines:] if len(all_lines) > lines else all_lines
                output = "".join(last)
                safe = escape(output)
                if len(safe) > 3000:
                    safe = safe[:3000] + "\n..."
                return f"<pre><code>{safe}</code></pre>"
        return "لا توجد مخرجات"
    except:
        return "خطأ في القراءة"

def update_token(path, new_token):
    keywords = ["TOKEN", "bot_token", "api_key", "tok", "TKN", "BOT_TKN", "API_TOKEN"]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        pattern = r"(['\"])\d{8,12}:[a-zA-Z0-9_-]{35,}(['\"])"
        new_content = re.sub(pattern, f"\\1{new_token}\\2", content)
        for kw in keywords:
            kw_pattern = rf"{kw}\s*=\s*(['\"])[^'\"]+(['\"])"
            new_content = re.sub(kw_pattern, f"{kw} = \\1{new_token}\\2", new_content)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except:
        return False

def check_token(token):
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        res = requests.get(url, timeout=15).json()
        if res.get("ok"):
            return True, res["result"]
        return False, res.get("description")
    except Exception as e:
        return False, str(e)

def gen_id(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def set_cancel(uid, state=True):
    cancel_states[uid] = state

def is_cancelled(uid):
    return cancel_states.get(uid, False)

def clear_cancel(uid):
    if uid in cancel_states:
        del cancel_states[uid]

def get_thumb():
    settings = get_settings()
    thumb = settings.get('file_thumb')
    if thumb and os.path.exists(thumb):
        return thumb
    return None

def locked_msg(chat_id):
    text = "البوت مغلق حالياً\n\nتم إيقاف الخدمة مؤقتاً\n\nيمكنك التواصل عبر الزر أدناه."
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("الدعم", url=f"tg://user?id={ADMIN_ID}", style="success", icon_custom_emoji_id="5224668724484652477"))
    send_msg(chat_id, text, markup)

def start_script(fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return False
    
    file_info = files[fid]
    user_id = file_info.get('user_id')
    
    if not verify_file_access(fid, user_id):
        return False
    
    encrypted_content = load_encrypted_file(fid)
    if not encrypted_content:
        return False
    
    env_dir = os.path.join(ENV_DIR, fid)
    if not os.path.exists(env_dir):
        os.makedirs(env_dir)
    
    env_file_path = os.path.join(env_dir, f"{fid}.py")
    
    if fid in active_processes and active_processes[fid].poll() is None:
        return True
    
    try:
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write(encrypted_content)
    except:
        return False
    
    log_path = os.path.join(LOGS_DIR, f"{fid}.log")
    try:
        log_file = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, "-u", env_file_path],
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.PIPE,
            cwd=env_dir,
            start_new_session=True,
            env={**os.environ, "PYTHONPATH": env_dir}
        )
        active_processes[fid] = proc
        return True
    except:
        return False

def stop_script(fid):
    if fid in active_processes:
        proc = active_processes[fid]
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except:
            try:
                proc.terminate()
            except:
                pass
        del active_processes[fid]
        if fid in process_hours:
            del process_hours[fid]
        return True
    return False

def stop_all_scripts():
    for fid in list(active_processes.keys()):
        stop_script(fid)
    return True

def write_proc(fid, cmd):
    if fid in active_processes and active_processes[fid].poll() is None:
        try:
            proc = active_processes[fid]
            if proc.stdin:
                proc.stdin.write(cmd.encode('utf-8') + b'\n')
                proc.stdin.flush()
                return True
        except:
            pass
    return False

def create_zip(files_list, zip_name):
    zip_path = os.path.join(BASE_DIR, zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_path in files_list:
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))
    return zip_path

def auto_fix_errors(code):
    fixes = [
        (r'print\s+(\S+)', r'print(\1)'),
        (r'raw_input', 'input'),
        (r'xrange', 'range'),
        (r'\.iteritems\(\)', '.items()'),
        (r'\.itervalues\(\)', '.values()'),
        (r'\.iterkeys\(\)', '.keys()'),
    ]
    for pattern, replacement in fixes:
        code = re.sub(pattern, replacement, code)
    return code

# ===== القائمة الرئيسية (بدون إيموجي) =====
def main_kb(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("رفع ملف", callback_data="nav_upload", style="danger", icon_custom_emoji_id="5800835941543186089"))
    kb.row(
        types.InlineKeyboardButton("ملفاتي", callback_data="nav_files", style="primary", icon_custom_emoji_id="5431420628978641216"),
        types.InlineKeyboardButton("تثبيت مكتبة", callback_data="nav_lib", style="danger", icon_custom_emoji_id="4947267906506327181")
    )
    kb.row(
        types.InlineKeyboardButton("رابط الدعوة", callback_data="ref", style="primary", icon_custom_emoji_id="5307803928237199877"),
        types.InlineKeyboardButton("الدعم", url=OWNER_URL, style="danger", icon_custom_emoji_id="5224668724484652477")
    )
    kb.row(
        types.InlineKeyboardButton("المطور", url=OWNER_URL),
        types.InlineKeyboardButton("القناة الرسمية", url=CHANNEL_URL)
    )
    if is_admin(uid):
        kb.add(types.InlineKeyboardButton("لوحة الإدارة", callback_data="nav_admin", style="danger", icon_custom_emoji_id="5330399283030013876"))
    return kb

# ===== لوحة الإدارة (كل زرين في صف واحد) =====
def admin_panel(call):
    users = read_json(USERS_DB)
    files = read_json(FILES_DB)
    pending = [f for f in files.values() if f.get('status') == 'pending']
    active = sum(1 for fid in active_processes if active_processes[fid].poll() is None)
    settings = get_settings()
    locked = settings.get('bot_locked', False)
    text = f"المستخدمين: {len(users)}\nالملفات: {len(files)}\nالمعلقة: {len(pending)}\nالنشطة: {active}\nالأدمن: {len(get_admins())}\n\nحالة البوت: {'مغلق' if locked else 'مفتوح'}"
    
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("فتح" if locked else "قفل", callback_data="lock_bot"),
        types.InlineKeyboardButton("إضافة نقاط", callback_data="admin_add_points", style="success", icon_custom_emoji_id="5217822164362739968")
    )
    kb.add(
        types.InlineKeyboardButton("خصم نقاط", callback_data="admin_deduct_points", style="danger", icon_custom_emoji_id="5217822164362739968"),
        types.InlineKeyboardButton("تفعيل VIP", callback_data="admin_grant_vip", style="danger", icon_custom_emoji_id="5217822164362739968")
    )
    kb.add(
        types.InlineKeyboardButton("سحب VIP", callback_data="admin_revoke_vip", style="danger", icon_custom_emoji_id="5217822164362739968"),
        types.InlineKeyboardButton("حظر", callback_data="admin_ban_user", style="danger", icon_custom_emoji_id="5217822164362739968")
    )
    kb.add(
        types.InlineKeyboardButton("فك الحظر", callback_data="admin_unban_user", style="danger", icon_custom_emoji_id="5217822164362739968"),
        types.InlineKeyboardButton("الأدمن", callback_data="adm_admins", style="danger", icon_custom_emoji_id="5217822164362739968")
    )
    kb.add(
        types.InlineKeyboardButton("المتجر", callback_data="adm_store", style="danger", icon_custom_emoji_id="5217822164362739968"),
        types.InlineKeyboardButton("المعلقة", callback_data="adm_pending", style="danger", icon_custom_emoji_id="5217822164362739968")
    )
    kb.add(
        types.InlineKeyboardButton("إذاعة", callback_data="adm_broadcast", style="danger", icon_custom_emoji_id="5217822164362739968"),
        types.InlineKeyboardButton("القنوات", callback_data="adm_channels", style="danger", icon_custom_emoji_id="5217822164362739968")
    )
    kb.add(
        types.InlineKeyboardButton("الملفات", callback_data="adm_files", style="danger", icon_custom_emoji_id="5217822164362739968"),
        types.InlineKeyboardButton("إيقاف الكل", callback_data="stop_all", style="danger", icon_custom_emoji_id="5217822164362739968")
    )
    kb.add(
        types.InlineKeyboardButton("خصم رصيد الكل", callback_data="deduct_all", style="danger", icon_custom_emoji_id="5217822164362739968"),
        types.InlineKeyboardButton("الإعدادات", callback_data="adm_settings", style="danger", icon_custom_emoji_id="5217822164362739968")
    )
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_main", style="danger", icon_custom_emoji_id="5325867499827251758"))
    
    edit_msg(call, text, kb)

def cancel_kb(data="cancel"):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("إلغاء", callback_data=data, style="danger", icon_custom_emoji_id="5215697242177939628"))
    return kb

def back_kb(data="nav_main"):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("رجوع", callback_data=data, style="danger", icon_custom_emoji_id="5325867499827251758"))
    return kb

# ===== قائمة البوت الزرقاء (Menu Button) =====
def set_bot_menu():
    try:
        bot.set_my_commands([
            types.BotCommand("start", "بدء البوت"),
        ])
        print("✅ تم تعيين القائمة الزرقاء بنجاح!")
    except Exception as e:
        print(f"❌ فشل تعيين القائمة الزرقاء: {e}")

@bot.message_handler(commands=['start'])
def start_cmd(msg):
    try:
        uid = msg.from_user.id
        
        if is_bot_locked() and not is_admin(uid):
            locked_msg(msg.chat.id)
            return
        
        users = read_json(USERS_DB)
        clear_cancel(uid)
        
        ref_id = None
        if len(msg.text.split()) > 1:
            ref = msg.text.split()[1]
            if ref.isdigit() and int(ref) != uid:
                ref_id = int(ref)
        
        if str(uid) not in users:
            users[str(uid)] = {
                'username': msg.from_user.username,
                'first_name': msg.from_user.first_name,
                'last_name': msg.from_user.last_name,
                'points': 0,
                'join_date': str(datetime.now().date()),
                'is_banned': 0,
                'expiry': None,
                'notifications': True
            }
            write_json(USERS_DB, users)
            user_notifications[uid] = True
            
            if ref_id and str(ref_id) in users:
                users[str(ref_id)]['points'] = users[str(ref_id)].get('points', 0) + 1
                write_json(USERS_DB, users)
                try:
                    bot.send_message(ref_id, f"مكافأة إحالة\nقام مستخدم جديد باستخدام رابطك!\nحصلت على 1 نقطة!")
                except:
                    pass
            
            try:
                name = escape(f"{msg.from_user.first_name} {msg.from_user.last_name or ''}")
                uname = f"@{msg.from_user.username}" if msg.from_user.username else "لا يوجد"
                cap = f"مستخدم جديد\n\nالاسم: {name}\nالآيدي: <code>{uid}</code>\nالمعرف: {uname}\nالتاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                if ref_id:
                    cap += f"\nتمت الإحالة بواسطة: <code>{ref_id}</code>"
                for adm in get_admins():
                    try:
                        photos = bot.get_user_profile_photos(uid)
                        if photos.total_count > 0:
                            bot.send_photo(adm, photos.photos[0][-1].file_id, caption=cap, parse_mode="HTML")
                        else:
                            bot.send_message(adm, cap, parse_mode="HTML")
                    except:
                        pass
            except:
                pass
        
        users = read_json(USERS_DB)
        if users.get(str(uid), {}).get('is_banned', 0) == 1:
            return bot.send_message(msg.chat.id, f"محظور\nتم حظرك من البوت.")
        
        if not check_sub(uid):
            return sub_msg(msg.chat.id)
        
        u = users.get(str(uid), {})
        vip = is_user_pro(uid)
        
        welcome_msg = f"أهلاً بك يا {escape(msg.from_user.first_name or 'مستخدم')} في بوت الاستضافة\n\nالرتبة: {'VIP' if vip else 'مجاني'}\nنقاطك: {u.get('points', 0)}\n\n{PROJECT_RIGHTS}"
        
        send_msg(msg.chat.id, welcome_msg, main_kb(uid))
        
    except Exception as e:
        print(f"Start Error: {e}")

def sub_msg(chat_id):
    settings = get_settings()
    channels = settings.get('channels', [])
    if not channels:
        return
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        kb.add(types.InlineKeyboardButton(ch['name'], url=f"https://t.me/{ch['username'].replace('@', '')}"))
    kb.add(types.InlineKeyboardButton("تحقق", callback_data="check_sub", style="danger", icon_custom_emoji_id="4961128762402931736"))
    text = "اشتراك إجباري\n\nيجب الاشتراك في القنوات التالية:"
    send_msg(chat_id, text, kb)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    try:
        uid = call.from_user.id
        cid = call.message.chat.id
        data = call.data
        users = read_json(USERS_DB)
        
        if is_bot_locked() and not is_admin(uid):
            bot.answer_callback_query(call.id, "البوت مغلق!", show_alert=True)
            locked_msg(cid)
            return
        
        if str(uid) in users and users[str(uid)].get('is_banned', 0) == 1:
            return bot.answer_callback_query(call.id, "أنت محظور!", show_alert=True)
        
        if data == "cancel":
            set_cancel(uid, True)
            bot.answer_callback_query(call.id, "تم الإلغاء")
            u = users.get(str(uid), {})
            vip = is_user_pro(uid)
            welcome_msg = f"أهلاً بك في بوت الاستضافة\n\nالرتبة: {'VIP' if vip else 'مجاني'}\nنقاطك: {u.get('points', 0)}\n\n{PROJECT_RIGHTS}"
            edit_msg(call, welcome_msg, main_kb(uid))
            return
        
        if data == "cancel_admin":
            set_cancel(uid, True)
            bot.answer_callback_query(call.id, "تم الإلغاء")
            admin_panel(call)
            return
        
        if data == "check_sub":
            if check_sub(uid):
                bot.answer_callback_query(call.id, "تم التحقق!")
                u = users.get(str(uid), {})
                vip = is_user_pro(uid)
                welcome_msg = f"أهلاً بك في بوت الاستضافة\n\nالرتبة: {'VIP' if vip else 'مجاني'}\nنقاطك: {u.get('points', 0)}\n\n{PROJECT_RIGHTS}"
                edit_msg(call, welcome_msg, main_kb(uid))
            else:
                bot.answer_callback_query(call.id, "لم تشترك!", show_alert=True)
            return
        
        if not check_sub(uid) and not is_admin(uid):
            bot.answer_callback_query(call.id, "اشترك أولاً!", show_alert=True)
            return
        
        clear_cancel(uid)
        
        if data == "nav_main":
            u = users.get(str(uid), {})
            vip = is_user_pro(uid)
            welcome_msg = f"أهلاً بك في بوت الاستضافة\n\nالرتبة: {'VIP' if vip else 'مجاني'}\nنقاطك: {u.get('points', 0)}\n\n{PROJECT_RIGHTS}"
            edit_msg(call, welcome_msg, main_kb(uid))
        
        elif data == "ref":
            info = bot.get_me()
            link = f"https://t.me/{info.username}?start={uid}"
            text = f"رابطك:\n<code>{link}</code>\n\nكل شخص يستخدم رابطك = 1 نقطة!"
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_main", style="danger", icon_custom_emoji_id="5325867499827251758"))
            edit_msg(call, text, kb)
        
        elif data == "nav_upload":
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل ملف .py:", reply_markup=cancel_kb())
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, upload_step, m.message_id)
        
        elif data == "nav_files":
            files = read_json(FILES_DB)
            u_files = {fid: f for fid, f in files.items() if f.get('user_id') == uid and f.get('status') == 'active'}
            if not u_files:
                return bot.answer_callback_query(call.id, "لا ملفات!", show_alert=True)
            kb = types.InlineKeyboardMarkup(row_width=1)
            for fid, f in u_files.items():
                running = fid in active_processes and active_processes[fid].poll() is None
                icon = "يعمل" if running else "متوقف"
                ft = "VIP" if f.get('type') == 'pro' else "مجاني"
                kb.add(types.InlineKeyboardButton(f"{icon} {ft} {f.get('file_name', '?')[:25]}", callback_data=f"manage_{fid}"))
            kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_main", style="danger", icon_custom_emoji_id="5325867499827251758"))
            running_count = sum(1 for fid in u_files if fid in active_processes and active_processes[fid].poll() is None)
            text = f"الملفات: {len(u_files)}\nتعمل: {running_count}\nمتوقفة: {len(u_files) - running_count}"
            edit_msg(call, text, kb)
        
        elif data.startswith("manage_"):
            file_panel(call, data.split("_")[1])
        
        elif data.startswith("toggle_"):
            toggle_file(call, data.split("_")[1])
        
        elif data.startswith("delc_"):
            fid = data.split("_")[1]
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("نعم", callback_data=f"del_{fid}", style="danger", icon_custom_emoji_id="5260726538302660868"),
                types.InlineKeyboardButton("لا", callback_data=f"manage_{fid}", style="danger", icon_custom_emoji_id="6294186186156017543")
            )
            edit_msg(call, "هل تريد حذف الملف؟", kb)
        
        elif data.startswith("del_"):
            delete_file(call, data.split("_")[1])
        
        elif data.startswith("dl_"):
            download_file(call, data.split("_")[1])
        
        elif data.startswith("term_"):
            terminal(call, data.split("_")[1])
        
        elif data.startswith("rterm_"):
            terminal(call, data.split("_")[1])
        
        elif data.startswith("inp_"):
            fid = data.split("_")[1]
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "اكتب الأمر:", reply_markup=cancel_kb())
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, input_step, fid, m.message_id)
        
        elif data.startswith("chtoken_"):
            fid = data.split("_")[1]
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل التوكن:", reply_markup=cancel_kb())
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, token_step, fid, m.message_id)
        
        elif data.startswith("tokinfo_"):
            token_info(call, data.split("_")[1])
        
        elif data == "nav_lib":
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل اسم المكتبة:", reply_markup=cancel_kb())
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, lib_step, m.message_id)
        
        elif data == "nav_admin" and is_admin(uid):
            admin_panel(call)
        
        elif data == "lock_bot" and is_admin(uid):
            new = toggle_bot_lock()
            st = "مغلق" if new else "مفتوح"
            bot.answer_callback_query(call.id, f"البوت {st}")
            admin_panel(call)
        
        elif data == "admin_add_points" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الآيدي وعدد النقاط مفصولة بمسافة (مثال: 123456789 10):", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_add_points_step, m.message_id)
        
        elif data == "admin_deduct_points" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الآيدي وعدد النقاط مفصولة بمسافة (مثال: 123456789 5):", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_deduct_points_step, m.message_id)
        
        elif data == "admin_grant_vip" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الآيدي وعدد الأيام (0 للدائم) مفصولة بمسافة (مثال: 123456789 30):", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_grant_vip_step, m.message_id)
        
        elif data == "admin_revoke_vip" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الآيدي:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_revoke_vip_step, m.message_id)
        
        elif data == "admin_ban_user" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الآيدي:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_ban_user_step, m.message_id)
        
        elif data == "admin_unban_user" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الآيدي:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, admin_unban_user_step, m.message_id)
        
        elif data == "adm_admins" and is_admin(uid):
            admins_panel(call)
        
        elif data == "add_admin" and is_main_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل آيدي المستخدم:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, add_admin_step, m.message_id)
        
        elif data == "add_admin" and not is_main_admin(uid):
            bot.answer_callback_query(call.id, "فقط المالك الرئيسي!", show_alert=True)
        
        elif data.startswith("rmadmin_") and is_admin(uid):
            aid = int(data.split("_")[1])
            if aid == ADMIN_ID:
                bot.answer_callback_query(call.id, "لا يمكن إزالة المالك!", show_alert=True)
            elif not is_main_admin(uid) and aid != uid:
                bot.answer_callback_query(call.id, "فقط المالك يمكنه!", show_alert=True)
            elif remove_admin(aid):
                bot.answer_callback_query(call.id, "تم إزالة الأدمن")
                admins_panel(call)
            else:
                bot.answer_callback_query(call.id, "فشل!", show_alert=True)
        
        elif data == "adm_store" and is_admin(uid):
            store_panel(call)
        
        elif data == "add_store" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الملف:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, store_add_step, m.message_id)
        
        elif data.startswith("estore_"):
            store_edit(call, data.split("_")[1])
        
        elif data.startswith("sprice_"):
            sid = data.split("_")[1]
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل السعر:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, store_price_step, sid, m.message_id)
        
        elif data.startswith("delstore_"):
            store_del(call, data.split("_")[1])
        
        elif data == "adm_pending" and is_admin(uid):
            pending_list(call)
        
        elif data.startswith("vpend_") and is_admin(uid):
            pending_view(call, data.split("_")[1])
        
        elif data.startswith("approve_") and is_admin(uid):
            approve_file(call, data.split("_")[1])
        
        elif data.startswith("reject_") and is_admin(uid):
            reject_file(call, data.split("_")[1])
        
        elif data == "adm_broadcast" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل رسالتك:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, broadcast_step, m.message_id)
        
        elif data == "adm_settings" and is_admin(uid):
            settings_panel(call)
        
        elif data == "adm_channels" and is_admin(uid):
            channels_panel(call)
        
        elif data == "add_channel" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل معرف القناة (@...):", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, add_channel_step, m.message_id)
        
        elif data.startswith("delch_") and is_admin(uid):
            del_channel(call, int(data.split("_")[1]))
        
        elif data == "set_img" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الصورة:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, img_step, m.message_id)
        
        elif data == "rm_img" and is_admin(uid):
            settings = get_settings()
            settings['bot_image'] = None
            save_settings(settings)
            bot.answer_callback_query(call.id, "تم إزالة الصورة")
            settings_panel(call)
        
        elif data == "set_thumb" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الصورة:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, thumb_step, m.message_id)
        
        elif data == "rm_thumb" and is_admin(uid):
            settings = get_settings()
            if settings.get('file_thumb') and os.path.exists(settings.get('file_thumb', '')):
                try:
                    os.remove(settings['file_thumb'])
                except:
                    pass
            settings['file_thumb'] = None
            save_settings(settings)
            bot.answer_callback_query(call.id, "تم إزالة الأيقونة")
            settings_panel(call)
        
        elif data == "set_name" and is_admin(uid):
            try:
                bot.delete_message(cid, call.message.message_id)
            except:
                pass
            m = bot.send_message(cid, "أرسل الاسم:", reply_markup=cancel_kb("cancel_admin"))
            save_message(cid, m.message_id)
            bot.register_next_step_handler(m, name_step, m.message_id)
        
        elif data == "stop_all" and is_admin(uid):
            files = read_json(FILES_DB)
            for fid in list(active_processes.keys()):
                stop_script(fid)
            for fid in list(files.keys()):
                try:
                    encrypted_path = os.path.join(ENCRYPTED_DIR, f"{fid}.enc")
                    if os.path.exists(encrypted_path):
                        os.remove(encrypted_path)
                    log_path = os.path.join(LOGS_DIR, f"{fid}.log")
                    if os.path.exists(log_path):
                        os.remove(log_path)
                    env_dir = os.path.join(ENV_DIR, fid)
                    if os.path.exists(env_dir):
                        import shutil
                        shutil.rmtree(env_dir, ignore_errors=True)
                except:
                    pass
            write_json(FILES_DB, {})
            bot.answer_callback_query(call.id, "تم إيقاف وحذف جميع البوتات")
            admin_panel(call)
        
        elif data == "deduct_all" and is_admin(uid):
            users = read_json(USERS_DB)
            for uid_str in users:
                users[uid_str]['points'] = 0
            write_json(USERS_DB, users)
            bot.answer_callback_query(call.id, "تم خصم رصيد جميع المستخدمين")
            admin_panel(call)
        
        elif data == "adm_files" and is_admin(uid):
            all_files_panel(call)
        
        elif data.startswith("afpage_"):
            page = int(data.split("_")[1])
            all_files_panel(call, page)
        
        elif data.startswith("afile_"):
            fid = data.split("_")[1]
            file_panel_admin(call, fid)
        
        elif data == "download_all_files" and is_admin(uid):
            all_files = read_json(FILES_DB)
            decrypted_files = []
            for fid in all_files.keys():
                if verify_file_access(fid, ADMIN_ID):
                    content = load_encrypted_file(fid)
                    if content:
                        temp_path = os.path.join(BASE_DIR, f"temp_{fid}_{gen_id(4)}.py")
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        decrypted_files.append(temp_path)
            if decrypted_files:
                zip_name = f"all_files_{gen_id(4)}.zip"
                zip_path = create_zip(decrypted_files, zip_name)
                try:
                    with open(zip_path, 'rb') as f:
                        bot.send_document(cid, f, caption="جميع ملفات البوت")
                    for temp_file in decrypted_files:
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    os.remove(zip_path)
                except:
                    bot.answer_callback_query(call.id, "فشل في التحميل!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, "لا ملفات للتحميل!", show_alert=True)
    
    except Exception as e:
        print(f"Callback Error: {e}")

def admin_add_points_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text:
        return
    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip('-').isdigit():
        send_msg(msg.chat.id, "تنسيق غير صحيح! أرسل الآيدي وعدد النقاط (مثال: 123456789 10)", back_kb("nav_admin"))
        return
    target_id = int(parts[0])
    amount = int(parts[1])
    users = read_json(USERS_DB)
    if str(target_id) not in users:
        send_msg(msg.chat.id, "المستخدم غير موجود!", back_kb("nav_admin"))
        return
    users[str(target_id)]['points'] = users[str(target_id)].get('points', 0) + amount
    write_json(USERS_DB, users)
    try:
        bot.send_message(target_id, f"إضافة نقاط\nتم إضافة {amount} نقطة إلى رصيدك!")
    except:
        pass
    send_msg(msg.chat.id, f"تم إضافة {amount} نقطة للمستخدم <code>{target_id}</code>", back_kb("nav_admin"))

def admin_deduct_points_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text:
        return
    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].lstrip('-').isdigit():
        send_msg(msg.chat.id, "تنسيق غير صحيح! أرسل الآيدي وعدد النقاط (مثال: 123456789 5)", back_kb("nav_admin"))
        return
    target_id = int(parts[0])
    amount = int(parts[1])
    users = read_json(USERS_DB)
    if str(target_id) not in users:
        send_msg(msg.chat.id, "المستخدم غير موجود!", back_kb("nav_admin"))
        return
    current = users[str(target_id)].get('points', 0)
    if amount > current:
        send_msg(msg.chat.id, f"الرصيد الحالي {current} نقطة فقط!", back_kb("nav_admin"))
        return
    users[str(target_id)]['points'] = current - amount
    write_json(USERS_DB, users)
    try:
        bot.send_message(target_id, f"خصم نقاط\nتم خصم {amount} نقطة من رصيدك!")
    except:
        pass
    send_msg(msg.chat.id, f"تم خصم {amount} نقطة من المستخدم <code>{target_id}</code>", back_kb("nav_admin"))

def admin_grant_vip_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text:
        return
    parts = msg.text.strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        send_msg(msg.chat.id, "تنسيق غير صحيح! أرسل الآيدي وعدد الأيام (مثال: 123456789 30) أو 0 للدائم", back_kb("nav_admin"))
        return
    target_id = int(parts[0])
    days = int(parts[1])
    users = read_json(USERS_DB)
    if str(target_id) not in users:
        send_msg(msg.chat.id, "المستخدم غير موجود!", back_kb("nav_admin"))
        return
    if days == 0:
        users[str(target_id)]['expiry'] = 'LIFETIME'
        exp_text = "دائم"
    else:
        exp_date = datetime.now() + timedelta(days=days)
        users[str(target_id)]['expiry'] = exp_date.strftime("%Y-%m-%d %H:%M:%S")
        exp_text = f"{days} يوم"
    write_json(USERS_DB, users)
    try:
        bot.send_message(target_id, f"تفعيل VIP\nتم ترقيتك إلى VIP!\nالمدة: {exp_text}")
    except:
        pass
    send_msg(msg.chat.id, f"تم منح VIP للمستخدم <code>{target_id}</code> لمدة {exp_text}", back_kb("nav_admin"))

def admin_revoke_vip_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, "أرسل الآيدي فقط!", back_kb("nav_admin"))
        return
    target_id = int(msg.text.strip())
    users = read_json(USERS_DB)
    if str(target_id) not in users:
        send_msg(msg.chat.id, "المستخدم غير موجود!", back_kb("nav_admin"))
        return
    users[str(target_id)]['expiry'] = None
    write_json(USERS_DB, users)
    try:
        bot.send_message(target_id, "تم إلغاء صلاحية VIP الخاصة بك!")
    except:
        pass
    send_msg(msg.chat.id, f"تم سحب VIP من المستخدم <code>{target_id}</code>", back_kb("nav_admin"))

def admin_ban_user_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, "أرسل الآيدي فقط!", back_kb("nav_admin"))
        return
    target_id = int(msg.text.strip())
    users = read_json(USERS_DB)
    if str(target_id) not in users:
        send_msg(msg.chat.id, "المستخدم غير موجود!", back_kb("nav_admin"))
        return
    users[str(target_id)]['is_banned'] = 1
    write_json(USERS_DB, users)
    try:
        bot.send_message(target_id, "تم حظرك من البوت!")
    except:
        pass
    send_msg(msg.chat.id, f"تم حظر المستخدم <code>{target_id}</code>", back_kb("nav_admin"))

def admin_unban_user_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, "أرسل الآيدي فقط!", back_kb("nav_admin"))
        return
    target_id = int(msg.text.strip())
    users = read_json(USERS_DB)
    if str(target_id) not in users:
        send_msg(msg.chat.id, "المستخدم غير موجود!", back_kb("nav_admin"))
        return
    users[str(target_id)]['is_banned'] = 0
    write_json(USERS_DB, users)
    try:
        bot.send_message(target_id, "تم فك حظرك من البوت!")
    except:
        pass
    send_msg(msg.chat.id, f"تم فك حظر المستخدم <code>{target_id}</code>", back_kb("nav_admin"))

def upload_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    
    if not msg.document or not (msg.document.file_name or '').lower().endswith('.py'):
        send_msg(msg.chat.id, "يجب ملف .py", back_kb("nav_upload"))
        return
    
    users = read_json(USERS_DB)
    u = users.get(str(uid), {})
    pts = u.get('points', 0)
    
    if not is_user_pro(uid):
        if pts < 1:
            info = bot.get_me()
            link = f"https://t.me/{info.username}?start={uid}"
            text = f"نقاط غير كافية!\n\nرصيدك: {pts}\nتحتاج نقطة واحدة على الأقل\n\nشارك رابط الدعوة واحصل على 1 نقطة:\n<code>{link}</code>"
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("مشاركة", url=f"https://t.me/share/url?url={link}", style="danger", icon_custom_emoji_id="5325613662965093403"))
            kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_main", style="danger", icon_custom_emoji_id="5325867499827251758"))
            send_msg(msg.chat.id, text, kb)
            return
        u['points'] = pts - 1
        users[str(uid)] = u
        write_json(USERS_DB, users)
        bot.send_message(msg.chat.id, f"تم خصم 1 نقطة\nرصيدك المتبقي: {u['points']}", parse_mode="HTML")
    
    fid = gen_id()
    finfo = bot.get_file(msg.document.file_id)
    file_content = bot.download_file(finfo.file_path).decode('utf-8')
    
    if not save_encrypted_file(fid, file_content, uid):
        send_msg(msg.chat.id, "فشل في حفظ الملف!", back_kb())
        return
    
    files = read_json(FILES_DB)
    files[fid] = {
        'user_id': uid,
        'file_name': msg.document.file_name,
        'type': 'pro' if is_user_pro(uid) else 'free',
        'status': 'pending',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'hours': 0
    }
    write_json(FILES_DB, files)
    
    user = bot.get_chat(uid)
    user_name = escape(f"{user.first_name} {user.last_name or ''}")
    user_mention = f"<a href='tg://user?id={uid}'>{user_name}</a>"
    admin_text = f"طلب رفع ملف جديد\n\nالمستخدم: {user_mention}\nالآيدي: <code>{uid}</code>\nاسم الملف: {escape(msg.document.file_name)}\nالنوع: {'VIP' if is_user_pro(uid) else 'مجاني'}\nالتاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    for adm in get_admins():
        try:
            doc = bot.send_document(adm, msg.document.file_id, caption=admin_text, parse_mode="HTML")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("موافقة", callback_data=f"approve_{fid}", style="danger", icon_custom_emoji_id="5996697874853795634"),
                types.InlineKeyboardButton("رفض", callback_data=f"reject_{fid}", style="danger", icon_custom_emoji_id="5836871984171981165")
            )
            bot.edit_message_caption(caption=admin_text + "\n\nفي انتظار المراجعة...", chat_id=adm, message_id=doc.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception as e:
            print(f"Error sending to admin: {e}")
    
    send_msg(uid, f"تم إرسال ملفك <b>{escape(msg.document.file_name)}</b> إلى الأدمن للمراجعة.\nسيتم إشعارك عند الموافقة أو الرفض.", back_kb())

def pending_list(call):
    files = read_json(FILES_DB)
    pending = {fid: f for fid, f in files.items() if f.get('status') == 'pending'}
    if not pending:
        return bot.answer_callback_query(call.id, "لا معلقات!", show_alert=True)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for fid, f in pending.items():
        ft = "VIP" if f.get('type') == 'pro' else "مجاني"
        kb.add(types.InlineKeyboardButton(f"{ft} {f.get('file_name', '?')[:25]}", callback_data=f"vpend_{fid}"))
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_admin", style="danger", icon_custom_emoji_id="5325867499827251758"))
    text = f"المعلقة: {len(pending)}"
    edit_msg(call, text, kb)

def pending_view(call, fid):
    files = read_json(FILES_DB)
    f = files.get(fid)
    if not f:
        return bot.answer_callback_query(call.id, "غير موجود!")
    content = load_encrypted_file(fid)
    if not content:
        preview = "تعذر قراءة الملف"
    else:
        safe = escape(content[:1000])
        if len(safe) > 3000:
            safe = safe[:3000] + "\n..."
        preview = f"<pre><code class='language-python'>{safe}</code></pre>"
    try:
        uinfo = bot.get_chat(f['user_id'])
        utext = f"{escape(uinfo.first_name)} (@{uinfo.username if uinfo.username else 'لا يوجد'})"
    except:
        utext = f"ID: {f['user_id']}"
    text = f"الملف: {f.get('file_name')}\nالمالك: {utext}\nالآيدي: <code>{f.get('user_id')}</code>\nالنوع: {'VIP' if f.get('type') == 'pro' else 'مجاني'}\nالمدة: دائم\nالتاريخ: {f.get('created_at')}\n\nالكود (أول 1000 حرف):\n{preview}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("قبول", callback_data=f"approve_{fid}", style="danger", icon_custom_emoji_id="5271518451087717901"),
        types.InlineKeyboardButton("رفض", callback_data=f"reject_{fid}", style="danger", icon_custom_emoji_id="6041716699848249286")
    )
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="adm_pending", style="danger", icon_custom_emoji_id="5325867499827251758"))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    m = bot.send_message(call.message.chat.id, text[:4000], parse_mode="HTML", reply_markup=kb)
    save_message(call.message.chat.id, m.message_id)

def approve_file(call, fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "غير موجود!")
    files[fid]['status'] = 'active'
    user_id = files[fid]['user_id']
    write_json(FILES_DB, files)
    start_script(fid)
    try:
        bot.send_message(user_id, f"تمت الموافقة على ملفك <b>{files[fid]['file_name']}</b>! يعمل الآن.")
    except:
        pass
    try:
        bot.edit_message_caption(
            caption=f"تمت الموافقة على الملف",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except:
        pass
    bot.answer_callback_query(call.id, "تم القبول!")
    pending_list(call)

def reject_file(call, fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "غير موجود!")
    user_id = files[fid]['user_id']
    fname = files[fid]['file_name']
    try:
        encrypted_path = os.path.join(ENCRYPTED_DIR, f"{fid}.enc")
        if os.path.exists(encrypted_path):
            os.remove(encrypted_path)
    except:
        pass
    
    security = read_json(SECURITY_DB)
    file_keys = security.get('file_keys', {})
    if fid in file_keys:
        del file_keys[fid]
        security['file_keys'] = file_keys
        write_json(SECURITY_DB, security)
    
    del files[fid]
    write_json(FILES_DB, files)
    try:
        bot.send_message(user_id, f"تم رفض ملفك <b>{fname}</b>.")
    except:
        pass
    try:
        bot.edit_message_caption(
            caption=f"تم رفض الملف",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except:
        pass
    bot.answer_callback_query(call.id, "تم الرفض")
    pending_list(call)

def file_panel(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "لا تملك صلاحية الوصول!", show_alert=True)
        return
    
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "غير موجود!")
    
    f = files[fid]
    content = load_encrypted_file(fid)
    if not content:
        preview = "تعذر قراءة الملف"
    else:
        safe = escape(content[:1000])
        if len(safe) > 3000:
            safe = safe[:3000] + "\n..."
        preview = f"<pre><code class='language-python'>{safe}</code></pre>"
    
    running = fid in active_processes and active_processes[fid].poll() is None
    text = f"الملف: {f.get('file_name')}\nالنوع: {'VIP' if f.get('type') == 'pro' else 'مجاني'}\nالحالة: {'يعمل' if running else 'متوقف'}\nالمدة: دائم\nالتاريخ: {f.get('created_at')}\n\nالكود (أول 1000 حرف):\n{preview}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("إيقاف" if running else "تشغيل", callback_data=f"toggle_{fid}"),
        types.InlineKeyboardButton("التيرمنال", callback_data=f"term_{fid}", style="danger", icon_custom_emoji_id="5330418941095325697")
    )
    kb.add(
        types.InlineKeyboardButton("تغيير التوكن", callback_data=f"chtoken_{fid}", style="danger", icon_custom_emoji_id="5220021677244559322"),
        types.InlineKeyboardButton("معلومات التوكن", callback_data=f"tokinfo_{fid}", style="danger", icon_custom_emoji_id="6028435952299413210")
    )
    kb.add(
        types.InlineKeyboardButton("تحميل", callback_data=f"dl_{fid}", style="danger", icon_custom_emoji_id="5433878454078556670"),
        types.InlineKeyboardButton("حذف", callback_data=f"delc_{fid}", style="danger", icon_custom_emoji_id="5870875489362513438")
    )
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_files", style="danger", icon_custom_emoji_id="5325867499827251758"))
    edit_msg(call, text, kb)

def toggle_file(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "لا تملك صلاحية الوصول!", show_alert=True)
        return
    
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "غير موجود!")
    
    running = fid in active_processes and active_processes[fid].poll() is None
    if running:
        stop_script(fid)
        bot.answer_callback_query(call.id, "تم الإيقاف")
    else:
        if start_script(fid):
            bot.answer_callback_query(call.id, "تم التشغيل")
        else:
            bot.answer_callback_query(call.id, "فشل!")
    file_panel(call, fid)

def delete_file(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "لا تملك صلاحية الوصول!", show_alert=True)
        return
    
    stop_script(fid)
    files = read_json(FILES_DB)
    if fid in files:
        fname = files[fid].get('file_name', '?')
        try:
            encrypted_path = os.path.join(ENCRYPTED_DIR, f"{fid}.enc")
            if os.path.exists(encrypted_path):
                os.remove(encrypted_path)
        except:
            pass
        
        try:
            os.remove(os.path.join(LOGS_DIR, f"{fid}.log"))
        except:
            pass
        
        try:
            env_dir = os.path.join(ENV_DIR, fid)
            import shutil
            shutil.rmtree(env_dir, ignore_errors=True)
        except:
            pass
        
        security = read_json(SECURITY_DB)
        file_keys = security.get('file_keys', {})
        if fid in file_keys:
            del file_keys[fid]
            security['file_keys'] = file_keys
            write_json(SECURITY_DB, security)
        
        del files[fid]
        write_json(FILES_DB, files)
        bot.answer_callback_query(call.id, f"تم حذف: {fname}")
    
    u_files = {fid: f for fid, f in files.items() if f.get('user_id') == uid and f.get('status') == 'active'}
    if not u_files:
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("رفع ملف", callback_data="nav_upload", style="danger", icon_custom_emoji_id="5319039176136477247"),
            types.InlineKeyboardButton("الرئيسية", callback_data="nav_main", style="danger", icon_custom_emoji_id="5429438067779855308")
        )
        edit_msg(call, "لا ملفات.", kb)
    else:
        kb = types.InlineKeyboardMarkup(row_width=1)
        for fid, f in u_files.items():
            running = fid in active_processes and active_processes[fid].poll() is None
            icon = "يعمل" if running else "متوقف"
            ft = "VIP" if f.get('type') == 'pro' else "مجاني"
            kb.add(types.InlineKeyboardButton(f"{icon} {ft} {f.get('file_name', '?')[:25]}", callback_data=f"manage_{fid}"))
        kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_main", style="danger", icon_custom_emoji_id="5325867499827251758"))
        edit_msg(call, f"الملفات: {len(u_files)}", kb)

def download_file(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "لا تملك صلاحية الوصول!", show_alert=True)
        return
    
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "غير موجود!")
    
    content = load_encrypted_file(fid)
    if not content:
        bot.answer_callback_query(call.id, "تعذر تحميل الملف!", show_alert=True)
        return
    
    try:
        temp_path = os.path.join(BASE_DIR, f"temp_{fid}_{gen_id(4)}.py")
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        thumb = get_thumb()
        with open(temp_path, 'rb') as f:
            if thumb:
                with open(thumb, 'rb') as t:
                    bot.send_document(call.message.chat.id, f, thumb=t, caption=f"{files[fid]['file_name']}", parse_mode="HTML")
            else:
                bot.send_document(call.message.chat.id, f, caption=f"{files[fid]['file_name']}", parse_mode="HTML")
        os.remove(temp_path)
        bot.answer_callback_query(call.id, "تم!")
    except:
        bot.answer_callback_query(call.id, "فشل!", show_alert=True)

def terminal(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "لا تملك صلاحية الوصول!", show_alert=True)
        return
    
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "غير موجود!")
    
    running = fid in active_processes and active_processes[fid].poll() is None
    output = get_logs(fid, 40)
    text = f"{files[fid]['file_name']}\n{'يعمل' if running else 'متوقف'}\n\nالتيرمنال:\n{output}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("تحديث", callback_data=f"rterm_{fid}", style="danger", icon_custom_emoji_id="5231311454048636466"),
        types.InlineKeyboardButton("إدخال", callback_data=f"inp_{fid}", style="danger", icon_custom_emoji_id="5253526631221307799")
    )
    kb.add(types.InlineKeyboardButton("رجوع", callback_data=f"manage_{fid}", style="danger", icon_custom_emoji_id="5325867499827251758"))
    edit_msg(call, text, kb)

def input_step(msg, fid, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text:
        return
    if write_proc(fid, msg.text):
        text = f"تم إرسال: <code>{escape(msg.text)}</code>"
    else:
        text = "الملف لا يعمل!"
    send_msg(msg.chat.id, text, back_kb(f"term_{fid}"))

def token_step(msg, fid, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text:
        return
    token = msg.text.strip()
    
    content = load_encrypted_file(fid)
    if not content:
        send_msg(msg.chat.id, "تعذر تحميل الملف!", back_kb(f"manage_{fid}"))
        return
    
    updated_content = update_token_in_memory(content, token)
    if updated_content:
        files = read_json(FILES_DB)
        if fid in files:
            user_id = files[fid].get('user_id')
            if save_encrypted_file(fid, updated_content, user_id):
                text = "تم تغيير التوكن!\n\nأعد تشغيل الملف."
            else:
                text = "فشل في حفظ التغييرات!"
        else:
            text = "الملف غير موجود!"
    else:
        text = "فشل في تحديث التوكن!"
    
    send_msg(msg.chat.id, text, back_kb(f"manage_{fid}"))

def update_token_in_memory(content, new_token):
    try:
        keywords = ["TOKEN", "bot_token", "api_key", "tok", "TKN", "BOT_TKN", "API_TOKEN"]
        pattern = r"(['\"])\d{8,12}:[a-zA-Z0-9_-]{35,}(['\"])"
        new_content = re.sub(pattern, f"\\1{new_token}\\2", content)
        for kw in keywords:
            kw_pattern = rf"{kw}\s*=\s*(['\"])[^'\"]+(['\"])"
            new_content = re.sub(kw_pattern, f"{kw} = \\1{new_token}\\2", new_content)
        return new_content
    except:
        return None

def token_info(call, fid):
    uid = call.from_user.id
    if not verify_file_access(fid, uid):
        bot.answer_callback_query(call.id, "لا تملك صلاحية الوصول!", show_alert=True)
        return
    
    content = load_encrypted_file(fid)
    if not content:
        bot.answer_callback_query(call.id, "تعذر تحميل الملف!", show_alert=True)
        return
    
    try:
        tokens = re.findall(r"(\d{8,12}:[a-zA-Z0-9_-]{35,})", content)
        if not tokens:
            return bot.answer_callback_query(call.id, "لا توكن!", show_alert=True)
        token = tokens[0]
        valid, info = check_token(token)
        if valid:
            text = f"التوكن صالح\n\nالاسم: {escape(info.get('first_name'))}\nالمعرف: @{info.get('username')}\nالآيدي: <code>{info.get('id')}</code>"
        else:
            text = f"التوكن غير صالح\n\n{escape(str(info))}"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("رجوع", callback_data=f"manage_{fid}", style="danger", icon_custom_emoji_id="5325867499827251758"))
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        m = bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=kb)
        save_message(call.message.chat.id, m.message_id)
    except:
        bot.answer_callback_query(call.id, "خطأ!", show_alert=True)

def lib_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text:
        return
    lib = msg.text.strip()
    m = bot.send_message(msg.chat.id, f"المكتبة: <b>{escape(lib)}</b>")
    save_message(msg.chat.id, m.message_id)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib], timeout=120)
        text = f"تم تثبيت: <b>{escape(lib)}</b>"
    except subprocess.TimeoutExpired:
        text = f"انتهت المهلة: <b>{escape(lib)}</b>"
    except:
        text = f"فشل: <b>{escape(lib)}</b>"
    bot.edit_message_text(text, msg.chat.id, m.message_id, parse_mode="HTML", reply_markup=back_kb())

def broadcast_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    users = read_json(USERS_DB)
    uids = list(users.keys())
    success, failed = 0, 0
    wait = bot.send_message(msg.chat.id, f"جاري الإرسال لـ {len(uids)} مستخدم...")
    save_message(msg.chat.id, wait.message_id)
    for user_id in uids:
        try:
            if msg.content_type == 'text':
                bot.send_message(user_id, msg.text, parse_mode="HTML")
            elif msg.content_type == 'photo':
                bot.send_photo(user_id, msg.photo[-1].file_id, caption=msg.caption, parse_mode="HTML")
            elif msg.content_type == 'document':
                bot.send_document(user_id, msg.document.file_id, caption=msg.caption, parse_mode="HTML")
            success += 1
            time.sleep(0.05)
        except:
            failed += 1
    text = f"اكتملت الإذاعة\n\nنجح: {success}\nفشل: {failed}\nالإجمالي: {len(uids)}"
    bot.edit_message_text(text, msg.chat.id, wait.message_id, parse_mode="HTML", reply_markup=back_kb("nav_admin"))

def channels_panel(call):
    settings = get_settings()
    channels = settings.get('channels', [])
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("إضافة قناة", callback_data="add_channel", style="danger", icon_custom_emoji_id="6010362983320916413"))
    for i, ch in enumerate(channels):
        kb.add(types.InlineKeyboardButton(f"حذف {ch['name']}", callback_data=f"delch_{i}"))
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_admin", style="danger", icon_custom_emoji_id="5325867499827251758"))
    text = f"القنوات: {len(channels)}"
    if channels:
        text += "\n\n"
        for ch in channels:
            text += f"{ch['name']} ({ch['username']})\n"
    edit_msg(call, text, kb)

def add_channel_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text:
        return
    username = msg.text.strip()
    if not username.startswith('@'):
        send_msg(msg.chat.id, "يجب أن يبدأ بـ @", back_kb("adm_channels"))
        return
    try:
        chat = bot.get_chat(username)
        settings = get_settings()
        settings['channels'] = settings.get('channels', []) + [{"username": username, "name": chat.title}]
        save_settings(settings)
        send_msg(msg.chat.id, f"تم إضافة: {chat.title}", back_kb("adm_channels"))
    except:
        send_msg(msg.chat.id, "لم أجد القناة!", back_kb("adm_channels"))

def del_channel(call, index):
    settings = get_settings()
    try:
        channels = settings.get('channels', [])
        if 0 <= index < len(channels):
            name = channels[index]['name']
            del channels[index]
            settings['channels'] = channels
            save_settings(settings)
            bot.answer_callback_query(call.id, f"تم حذف: {name}")
        channels_panel(call)
    except:
        bot.answer_callback_query(call.id, "خطأ!")

def settings_panel(call):
    settings = get_settings()
    has_img = "نعم" if settings.get('bot_image') else "لا"
    has_thumb = "نعم" if settings.get('file_thumb') and os.path.exists(settings.get('file_thumb', '')) else "لا"
    text = f"اسم البوت: {settings.get('bot_name', 'غير محدد')}\nصورة البوت: {has_img}\nأيقونة الملفات: {has_thumb}"
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("تغيير الاسم", callback_data="set_name", style="danger", icon_custom_emoji_id="5904754092609114390"))
    if settings.get('bot_image'):
        kb.add(
            types.InlineKeyboardButton("تغيير الصورة", callback_data="set_img", style="danger", icon_custom_emoji_id="5296541196842200155"),
            types.InlineKeyboardButton("إزالة الصورة", callback_data="rm_img", style="danger", icon_custom_emoji_id="5330234038458264989")
        )
    else:
        kb.add(types.InlineKeyboardButton("إضافة صورة", callback_data="set_img", style="danger", icon_custom_emoji_id="5870733514923577305"))
    if settings.get('file_thumb') and os.path.exists(settings.get('file_thumb', '')):
        kb.add(
            types.InlineKeyboardButton("تغيير الأيقونة", callback_data="set_thumb", style="danger", icon_custom_emoji_id="5192946667267043095"),
            types.InlineKeyboardButton("إزالة الأيقونة", callback_data="rm_thumb", style="danger", icon_custom_emoji_id="5904542823167824187")
        )
    else:
        kb.add(types.InlineKeyboardButton("إضافة أيقونة", callback_data="set_thumb", style="danger", icon_custom_emoji_id="5774034804450267485"))
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_admin", style="danger", icon_custom_emoji_id="5325867499827251758"))
    edit_msg(call, text, kb)

def name_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text:
        return
    settings = get_settings()
    settings['bot_name'] = msg.text.strip()
    save_settings(settings)
    send_msg(msg.chat.id, f"الاسم: {msg.text.strip()}", back_kb("adm_settings"))

def img_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.photo:
        send_msg(msg.chat.id, "أرسل صورة!", back_kb("adm_settings"))
        return
    try:
        fid = msg.photo[-1].file_id
        settings = get_settings()
        settings['bot_image'] = fid
        save_settings(settings)
        send_msg(msg.chat.id, "تم تحديث الصورة!", back_kb("adm_settings"))
    except:
        send_msg(msg.chat.id, "فشل!", back_kb("adm_settings"))

def thumb_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.photo:
        send_msg(msg.chat.id, "أرسل صورة!", back_kb("adm_settings"))
        return
    try:
        finfo = bot.get_file(msg.photo[-1].file_id)
        path = os.path.join(THUMBS_DIR, "thumb.jpg")
        with open(path, "wb") as f:
            f.write(bot.download_file(finfo.file_path))
        settings = get_settings()
        settings['file_thumb'] = path
        save_settings(settings)
        send_msg(msg.chat.id, "تم تحديث الأيقونة!", back_kb("adm_settings"))
    except:
        send_msg(msg.chat.id, "فشل!", back_kb("adm_settings"))

def admins_panel(call):
    uid = call.from_user.id
    admins = get_admins()
    text = f"الأدمن ({len(admins)}):\n\n"
    kb = types.InlineKeyboardMarkup(row_width=1)
    if is_main_admin(uid):
        kb.add(types.InlineKeyboardButton("إضافة أدمن", callback_data="add_admin", style="danger", icon_custom_emoji_id="5406711411541823609"))
    for aid in admins:
        try:
            user = bot.get_chat(aid)
            name = user.first_name
            owner = "المالك" if aid == ADMIN_ID else "أدمن"
            text += f"{owner} {escape(name)} - <code>{aid}</code>\n"
            if aid != ADMIN_ID and is_main_admin(uid):
                kb.add(types.InlineKeyboardButton(f"إزالة {name[:10]}", callback_data=f"rmadmin_{aid}"))
        except:
            text += f"أدمن <code>{aid}</code>\n"
            if aid != ADMIN_ID and is_main_admin(uid):
                kb.add(types.InlineKeyboardButton(f"إزالة {aid}", callback_data=f"rmadmin_{aid}"))
    if not is_main_admin(uid):
        text += "\n\nفقط المالك يمكنه إضافة/إزالة أدمن"
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_admin", style="danger", icon_custom_emoji_id="5325867499827251758"))
    edit_msg(call, text, kb)

def add_admin_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not is_main_admin(uid):
        send_msg(msg.chat.id, "فقط المالك!", back_kb("adm_admins"))
        return
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, "آيدي غير صحيح!", back_kb("adm_admins"))
        return
    new_id = int(msg.text.strip())
    if add_admin(new_id):
        try:
            bot.send_message(new_id, "تم تعيينك أدمن!")
        except:
            pass
        text = f"تم إضافة: <code>{new_id}</code>"
    else:
        text = "موجود مسبقاً!"
    send_msg(msg.chat.id, text, back_kb("adm_admins"))

def store_panel(call):
    store = read_json(STORE_DB)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("إضافة ملف", callback_data="add_store", style="danger", icon_custom_emoji_id="5184146373766808280"))
    for sid, item in store.items():
        kb.add(types.InlineKeyboardButton(f"{item['name'][:20]} - {item['price']}pt", callback_data=f"estore_{sid}"))
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_admin", style="danger", icon_custom_emoji_id="5325867499827251758"))
    text = f"الملفات: {len(store)}"
    edit_msg(call, text, kb)

def store_add_step(msg, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.document:
        send_msg(msg.chat.id, "أرسل ملفاً!", back_kb("adm_store"))
        return
    m = bot.send_message(msg.chat.id, f"الملف: <b>{escape(msg.document.file_name)}</b>\n\nأرسل السعر:", reply_markup=cancel_kb("cancel_admin"))
    save_message(msg.chat.id, m.message_id)
    bot.register_next_step_handler(m, store_price_add_step, msg.document, m.message_id)

def store_price_add_step(msg, doc, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, "سعر غير صحيح!", back_kb("adm_store"))
        return
    sid = gen_id()
    store = read_json(STORE_DB)
    store[sid] = {'name': doc.file_name, 'price': int(msg.text.strip())}
    write_json(STORE_DB, store)
    finfo = bot.get_file(doc.file_id)
    with open(os.path.join(STORE_DIR, f"{sid}.py"), 'wb') as f:
        f.write(bot.download_file(finfo.file_path))
    send_msg(msg.chat.id, f"تم إضافة: {doc.file_name}\nالسعر: {msg.text}", back_kb("adm_store"))

def store_edit(call, sid):
    store = read_json(STORE_DB)
    item = store.get(sid)
    if not item:
        return
    text = f"الملف: {item['name']}\nالسعر: {item['price']}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("تغيير السعر", callback_data=f"sprice_{sid}", style="danger", icon_custom_emoji_id="6039495948353146588"),
        types.InlineKeyboardButton("حذف", callback_data=f"delstore_{sid}", style="danger", icon_custom_emoji_id="5408832111773757273")
    )
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="adm_store", style="danger", icon_custom_emoji_id="5325867499827251758"))
    edit_msg(call, text, kb)

def store_price_step(msg, sid, prompt_id):
    uid = msg.from_user.id
    if is_cancelled(uid):
        clear_cancel(uid)
        return
    del_msg(msg.chat.id, prompt_id, msg.message_id)
    if not msg.text or not msg.text.strip().isdigit():
        send_msg(msg.chat.id, "سعر غير صحيح!", back_kb("adm_store"))
        return
    store = read_json(STORE_DB)
    if sid in store:
        store[sid]['price'] = int(msg.text.strip())
        write_json(STORE_DB, store)
        send_msg(msg.chat.id, f"السعر: {msg.text}", back_kb("adm_store"))

def store_del(call, sid):
    store = read_json(STORE_DB)
    if sid in store:
        name = store[sid]['name']
        try:
            os.remove(os.path.join(STORE_DIR, f"{sid}.py"))
        except:
            pass
        del store[sid]
        write_json(STORE_DB, store)
        bot.answer_callback_query(call.id, f"تم حذف: {name}")
        store_panel(call)

def all_files_panel(call, page=0):
    files = read_json(FILES_DB)
    file_ids = list(files.keys())
    items_per_page = 10
    total_pages = (len(file_ids) + items_per_page - 1) // items_per_page
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_files = file_ids[start_idx:end_idx]
    kb = types.InlineKeyboardMarkup(row_width=2)
    for fid in page_files:
        f = files[fid]
        kb.add(types.InlineKeyboardButton(f"{f.get('file_name', '?')[:15]}", callback_data=f"afile_{fid}"))
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("السابق", callback_data=f"afpage_{page-1}", style="danger", icon_custom_emoji_id="5190744186562824300"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("التالي", callback_data=f"afpage_{page+1}", style="danger", icon_custom_emoji_id="6082220874264481487"))
    if nav_buttons:
        kb.row(*nav_buttons)
    kb.add(types.InlineKeyboardButton("تحميل الكل", callback_data="download_all_files", style="danger", icon_custom_emoji_id="5904693305936975591"))
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="nav_admin", style="danger", icon_custom_emoji_id="5325867499827251758"))
    text = f"الصفحة {page+1} من {total_pages}\nإجمالي الملفات: {len(files)}"
    edit_msg(call, text, kb)

def file_panel_admin(call, fid):
    files = read_json(FILES_DB)
    if fid not in files:
        return bot.answer_callback_query(call.id, "غير موجود!")
    f = files[fid]
    content = load_encrypted_file(fid)
    preview = "غير مصرح بالوصول"
    if content:
        safe = escape(content[:1000])
        if len(safe) > 3000:
            safe = safe[:3000] + "\n..."
        preview = f"<pre><code class='language-python'>{safe}</code></pre>"
    running = fid in active_processes and active_processes[fid].poll() is None
    text = f"الملف: {f.get('file_name')}\nالمستخدم: <code>{f.get('user_id')}</code>\nالنوع: {'VIP' if f.get('type') == 'pro' else 'مجاني'}\nالحالة: {'يعمل' if running else 'متوقف'}\nالتاريخ: {f.get('created_at')}\n\nالكود (أول 1000 حرف):\n{preview}"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("رجوع", callback_data="afpage_0", style="danger", icon_custom_emoji_id="5325867499827251758"))
    edit_msg(call, text, kb)

def monitor():
    while True:
        try:
            files = read_json(FILES_DB)
            for fid in list(active_processes.keys()):
                proc = active_processes.get(fid)
                if not proc or proc.poll() is not None:
                    if fid in active_processes:
                        del active_processes[fid]
                    continue
                if fid not in files:
                    continue
                uid = str(files[fid]['user_id'])
                if not check_sub(int(uid)):
                    stop_script(fid)
                    try:
                        bot.send_message(int(uid), f"تم إيقاف {files[fid]['file_name']} لعدم الاشتراك!")
                    except:
                        pass
                    continue
        except Exception as e:
            print(f"Monitor Error: {e}")
        time.sleep(3600)

threading.Thread(target=monitor, daemon=True).start()

init_db()

# ===== تعيين القائمة الزرقاء =====
set_bot_menu()

print("=" * 40)
print("ASAD HOSTING | @ASADALY1")
print("=" * 40)
print("✅ البوت يعمل الآن على الاستضافة!")

# ===== طريقة التشغيل المحسنة للسرعة =====
if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=30)
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(5)
