import os
import time
import uuid
import html
import logging
import threading
import sqlite3
import requests
import json
import telebot
from telebot import types
from flask import Flask, redirect

# ================= CONFIGURATION ================= #
BOT_TOKEN = "8821996158:AAGeNh3bxR4rACu_VzNpzJKT3kjAB_hZcRw"
ADMIN_IDS = [8876911955]
CHANNEL_CHAT_ID = -1004331555496
SUPPORT_USERNAME = "@onlysazzat"

# ✅ নতুন WID
ADEXIUM_WID = "603d8f80-1a46-46f5-8cc0-8b1ae00d8928"

PORT = int(os.environ.get("PORT", 5000))
SERVER_BASE_URL = os.environ.get("SERVER_URL", f"http://localhost:{PORT}")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ================= DATABASE ================= #
def get_db():
    conn = sqlite3.connect("earning_bot.db", timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            balance REAL DEFAULT 0.0,
            total_tasks INTEGER DEFAULT 0,
            referred_by INTEGER DEFAULT NULL,
            total_refers INTEGER DEFAULT 0,
            refer_earnings REAL DEFAULT 0.0,
            is_banned INTEGER DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER,
            target_ad_url TEXT,
            is_visited INTEGER DEFAULT 0,
            visited_at REAL DEFAULT NULL,
            is_claimed INTEGER DEFAULT 0,
            created_at REAL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            amount REAL,
            method TEXT,
            number TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        defaults = {
            "min_withdraw": "20",
            "per_task_reward": "0.10",
            "adexium_wid": ADEXIUM_WID,
            "min_wait_seconds": "15",
            "refer_commission_percent": "10",
            "min_refers_required": "5",
            "server_url": SERVER_BASE_URL
        }
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
            
        conn.commit()
        conn.close()
        print("✅ Database ready")
    except Exception as e:
        print(f"❌ DB Error: {e}")

init_db()

# ================= HELPERS ================= #
def get_setting(key):
    try:
        conn = get_db()
        res = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        conn.close()
        return res["value"] if res else ""
    except:
        return ""

def update_setting(key, value):
    try:
        conn = get_db()
        conn.execute("UPDATE settings SET value = ? WHERE key = ?", (str(value), key))
        conn.commit()
        conn.close()
    except:
        pass

def get_user(user_id):
    try:
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        return user
    except:
        return None

# ================= ADEXIUM API ================= #
def fetch_adexium_ad(user_id, first_name):
    """Adexium থেকে অ্যাড ফেচ করুন"""
    wid = get_setting("adexium_wid")
    url = "https://bid.tgads.live/bot-request"
    headers = {"Content-Type": "application/json"}
    data = {
        "wid": wid,
        "language": "en",
        "isPremium": False,
        "firstName": first_name or "User",
        "telegramId": str(user_id)
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"⚠️ Adexium Error: {e}")
    
    # ❌ API কাজ না করলে ফলব্যাক অ্যাড
    return {
        "image": "https://go.tgads.live/image.png",
        "clickUrl": "https://t.me/onlysazzat",
        "buttonText": "Visit Ad",
        "text": "📢 Click to earn free money!"
    }

# ================= FLASK ================= #
@app.route('/click/<token>')
def track_ad_click(token):
    try:
        conn = get_db()
        task = conn.execute("SELECT * FROM task_tokens WHERE token = ?", (token,)).fetchone()
        if task:
            conn.execute(
                "UPDATE task_tokens SET is_visited = 1, visited_at = ? WHERE token = ?",
                (time.time(), token)
            )
            conn.commit()
        conn.close()
    except:
        pass
    return redirect("https://t.me")

def run_flask():
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Flask Error: {e}")

threading.Thread(target=run_flask, daemon=True).start()

# ================= KEYBOARDS ================= #
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🎯 Task"),
        types.KeyboardButton("💰 Balance"),
        types.KeyboardButton("👥 Refer"),
        types.KeyboardButton("💳 Withdraw"),
        types.KeyboardButton("👤 My Account"),
        types.KeyboardButton("🛠 Support")
    )
    return markup

def admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
        types.InlineKeyboardButton("🚫 Ban", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ Unban", callback_data="admin_unban"),
        types.InlineKeyboardButton("➕ Add Balance", callback_data="admin_add_bal"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
    )
    return markup

# ================= COMMANDS ================= #
@bot.message_handler(commands=['start'])
def start_cmd(message):
    try:
        user_id = message.from_user.id
        name = message.from_user.first_name or "User"
        username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if not user:
            conn.execute("""
                INSERT INTO users (user_id, name, username, balance) 
                VALUES (?, ?, ?, 0.0)
            """, (user_id, name, username))
            conn.commit()
        conn.close()
        
        bot.send_message(
            user_id,
            f"👋 আসসালামু আলাইকুম, <b>{html.escape(name)}</b>!\n\n"
            "🎉 Easy Earn Bot-এ স্বাগতম!\n"
            "👇 Task বাটনে চাপ দিন:",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Start Error: {e}")

@bot.message_handler(func=lambda m: m.text == "🎯 Task")
def task_handler(message):
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        if not user: return
        
        reward = float(get_setting("per_task_reward") or 0.10)
        wait_time = int(get_setting("min_wait_seconds") or 15)
        server_url = get_setting("server_url").rstrip('/')
        
        # অ্যাড ফেচ করুন
        ad_data = fetch_adexium_ad(user_id, message.from_user.first_name)
        
        # অ্যাড ডেটা প্রস্তুত করুন
        ad_url = ad_data.get("clickUrl", "https://t.me")
        ad_image = ad_data.get("image")
        ad_text = html.escape(ad_data.get("text", "Sponsored Ad"))
        button_text = ad_data.get("buttonText", "Go!")
        
        token = f"{user_id}_{uuid.uuid4().hex[:8]}"
        
        conn = get_db()
        conn.execute(
            "INSERT INTO task_tokens (token, user_id, target_ad_url, created_at) VALUES (?, ?, ?, ?)",
            (token, user_id, ad_url, time.time())
        )
        conn.commit()
        conn.close()
        
        track_link = f"{server_url}/click/{token}"
        
        # ✅ Inline Keyboard তৈরি করুন
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(f"🔗 {button_text} (+৳{reward:.2f})", url=track_link),
            types.InlineKeyboardButton("✅ Verify", callback_data=f"v_{token}")
        )
        
        task_text = (
            f"🎯 <b>Task</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📢 {ad_text}\n\n"
            f"💵 Reward: ৳ {reward:.2f}\n"
            f"⏳ Wait: {wait_time} seconds\n\n"
            "⚠️ Click the link and wait, then verify!"
        )
        
        if ad_image and ad_image.startswith("http"):
            try:
                bot.send_photo(user_id, ad_image, caption=task_text, reply_markup=keyboard, parse_mode="HTML")
            except:
                bot.send_message(user_id, task_text, reply_markup=keyboard, parse_mode="HTML")
        else:
            bot.send_message(user_id, task_text, reply_markup=keyboard, parse_mode="HTML")
            
    except Exception as e:
        print(f"❌ Task Error: {e}")
        bot.send_message(message.chat.id, "❌ Try again!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("v_"))
def verify_callback(call):
    try:
        token = call.data.split("_", 1)[1]
        user_id = call.from_user.id
        
        conn = get_db()
        task = conn.execute("SELECT * FROM task_tokens WHERE token = ? AND user_id = ?", (token, user_id)).fetchone()
        
        if not task:
            conn.close()
            return bot.answer_callback_query(call.id, "❌ Invalid!", show_alert=True)
        
        if task["is_claimed"] == 1:
            conn.close()
            return bot.answer_callback_query(call.id, "⚠️ Already done!", show_alert=True)
        
        if task["is_visited"] == 0:
            conn.close()
            return bot.answer_callback_query(call.id, "❌ Click the link first!", show_alert=True)
        
        wait_time = int(get_setting("min_wait_seconds") or 15)
        time_spent = time.time() - float(task["created_at"])
        
        if time_spent < wait_time:
            conn.close()
            remaining = int(wait_time - time_spent)
            return bot.answer_callback_query(call.id, f"⏳ Wait {remaining} seconds!", show_alert=True)
        
        # ✅ সফল
        reward = float(get_setting("per_task_reward") or 0.10)
        
        conn.execute("UPDATE task_tokens SET is_claimed = 1 WHERE token = ?", (token,))
        conn.execute("UPDATE users SET balance = balance + ?, total_tasks = total_tasks + 1 WHERE user_id = ?", (reward, user_id))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, f"✅ +৳{reward:.2f} Added!", show_alert=True)
        
    except Exception as e:
        print(f"❌ Verify Error: {e}")

# ================= BALANCE & OTHERS ================= #
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance_handler(message):
    user = get_user(message.from_user.id)
    if user:
        bot.send_message(
            message.chat.id,
            f"💰 Balance: ৳ {user['balance']:.2f}\n"
            f"🎯 Tasks: {user['total_tasks']}",
            parse_mode="HTML"
        )

@bot.message_handler(func=lambda m: m.text == "👥 Refer")
def refer_handler(message):
    bot_uname = bot.get_me().username or "EasyEarn72_bd_bot"
    ref_link = f"https://t.me/{bot_uname}?start={message.from_user.id}"
    bot.send_message(
        message.chat.id,
        f"🔗 Your Refer Link:\n<code>{ref_link}</code>\n\n"
        "Share with friends and earn!",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: m.text == "💳 Withdraw")
def withdraw_handler(message):
    bot.send_message(message.chat.id, "💳 Minimum withdraw: ৳20\nContact: @onlysazzat")

@bot.message_handler(func=lambda m: m.text == "👤 My Account")
def account_handler(message):
    user = get_user(message.from_user.id)
    if user:
        bot.send_message(
            message.chat.id,
            f"👤 Name: {user['name']}\n"
            f"💰 Balance: ৳ {user['balance']:.2f}\n"
            f"🎯 Tasks: {user['total_tasks']}",
            parse_mode="HTML"
        )

@bot.message_handler(func=lambda m: m.text == "🛠 Support")
def support_handler(message):
    bot.send_message(message.chat.id, f"📞 Support: {SUPPORT_USERNAME}")

# ================= ADMIN ================= #
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "👑 Admin Panel", reply_markup=admin_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        return bot.answer_callback_query(call.id, "❌ Not admin!", show_alert=True)
    
    if call.data == "admin_stats":
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'").fetchone()[0]
        conn.close()
        bot.send_message(call.message.chat.id, f"📊 Total Users: {total}\n⏳ Pending: {pending}")

# ================= MAIN ================= #
if __name__ == "__main__":
    print("=" * 40)
    print("🚀 Bot Starting...")
    print(f"🎯 WID: {ADEXIUM_WID}")
    print("=" * 40)
    
    while True:
        try:
            bot.infinity_polling(timeout=30, skip_pending=True)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)
