import os
import time
import uuid
import html
import logging
import sqlite3
import requests
import json
import telebot
from telebot import types
from flask import Flask, redirect
import threading

# ================= CONFIG ================= #
BOT_TOKEN = "8821996158:AAGeNh3bxR4rACu_VzNpzJKT3kjAB_hZcRw"
ADMIN_IDS = [8876911955]
CHANNEL_CHAT_ID = -1004331555496
SUPPORT_USERNAME = "@onlysazzat"
ADEXIUM_WID = "603d8f80-1a46-46f5-8cc0-8b1ae00d8928"

PORT = int(os.environ.get("PORT", 5000))
SERVER_BASE_URL = os.environ.get("SERVER_URL", f"http://localhost:{PORT}")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ================= LOGGING ================= #
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================= DATABASE ================= #
def get_db():
    try:
        conn = sqlite3.connect("bot_data.db", timeout=60, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn
    except Exception as e:
        logger.error(f"DB connection error: {e}")
        return None

def init_db():
    try:
        conn = get_db()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                balance REAL DEFAULT 0,
                total_tasks INTEGER DEFAULT 0,
                referred_by INTEGER,
                total_refers INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                token TEXT PRIMARY KEY,
                user_id INTEGER,
                ad_url TEXT,
                is_visited INTEGER DEFAULT 0,
                is_claimed INTEGER DEFAULT 0,
                created_at REAL,
                visited_at REAL
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Withdrawals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                method TEXT,
                number TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Default settings
        defaults = {
            'min_withdraw': '20',
            'per_task_reward': '0.10',
            'adexium_wid': ADEXIUM_WID,
            'min_wait_seconds': '15',
            'refer_commission': '10',
            'server_url': SERVER_BASE_URL
        }
        
        for key, value in defaults.items():
            cursor.execute(
                'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
                (key, value)
            )
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")
        
    except Exception as e:
        logger.error(f"❌ DB init error: {e}")

init_db()

# ================= HELPERS ================= #
def get_setting(key):
    try:
        conn = get_db()
        if not conn:
            return ""
        result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        conn.close()
        return result['value'] if result else ""
    except:
        return ""

def get_user(user_id):
    try:
        conn = get_db()
        if not conn:
            return None
        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        conn.close()
        return user
    except:
        return None

def create_user(user_id, name, username):
    try:
        conn = get_db()
        if not conn:
            return
        conn.execute(
            'INSERT OR IGNORE INTO users (user_id, name, username, balance) VALUES (?, ?, ?, 0)',
            (user_id, name, username)
        )
        conn.commit()
        conn.close()
        logger.info(f"✅ New user: {user_id}")
    except Exception as e:
        logger.error(f"❌ Create user error: {e}")

# ================= ADEXIUM API ================= #
def get_adexium_ad(user_id, name):
    """Adexium থেকে অ্যাড নিন, না পেলে ফলব্যাক দিন"""
    wid = get_setting('adexium_wid')
    url = "https://bid.tgads.live/bot-request"
    
    data = {
        "wid": wid,
        "language": "en",
        "isPremium": False,
        "firstName": name or "User",
        "telegramId": str(user_id)
    }
    
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=data,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Ad fetched for {user_id}")
            return result
        else:
            logger.warning(f"⚠️ API status: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ API error: {e}")
    
    # ❌ API কাজ না করলে ফলব্যাক অ্যাড
    return {
        "image": "https://go.tgads.live/image.png",
        "clickUrl": "https://t.me/onlysazzat",
        "buttonText": "Visit Ad",
        "text": "📢 Sponsored Content - Click to Earn!"
    }

# ================= FLASK SERVER ================= #
@app.route('/click/<token>')
def track_click(token):
    try:
        conn = get_db()
        if conn:
            conn.execute(
                'UPDATE tasks SET is_visited = 1, visited_at = ? WHERE token = ?',
                (time.time(), token)
            )
            conn.commit()
            conn.close()
            logger.info(f"✅ Click tracked: {token}")
    except:
        pass
    return redirect("https://t.me")

def run_flask():
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Flask error: {e}")

threading.Thread(target=run_flask, daemon=True).start()

# ================= KEYBOARDS ================= #
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "🎯 Task",
        "💰 Balance",
        "👥 Refer",
        "💳 Withdraw",
        "👤 My Account",
        "🛠 Support"
    ]
    row1 = [types.KeyboardButton(buttons[0]), types.KeyboardButton(buttons[1])]
    row2 = [types.KeyboardButton(buttons[2]), types.KeyboardButton(buttons[3])]
    row3 = [types.KeyboardButton(buttons[4]), types.KeyboardButton(buttons[5])]
    markup.row(row1[0], row1[1])
    markup.row(row2[0], row2[1])
    markup.row(row3[0], row3[1])
    return markup

# ================= COMMANDS ================= #
@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        user_id = message.from_user.id
        name = message.from_user.first_name or "User"
        username = message.from_user.username or ""
        
        create_user(user_id, name, username)
        
        welcome = f"""
👋 আসসালামু আলাইকুম, <b>{html.escape(name)}</b>!

🎉 <b>Easy Earn Bot-এ স্বাগতম!</b>

💰 অ্যাড দেখে আয় করুন
👥 বন্ধুদের রেফার করে আয় করুন
💳 সরাসরি উইথড্র করুন

👇 শুরু করতে <b>🎯 Task</b> বাটনে ক্লিক করুন
"""
        bot.send_message(user_id, welcome, reply_markup=main_menu(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Start error: {e}")
        bot.send_message(message.chat.id, "❌ দয়া করে আবার চেষ্টা করুন")

# ================= TASK ================= #
@bot.message_handler(func=lambda m: m.text == "🎯 Task")
def task_command(message):
    try:
        user_id = message.from_user.id
        user = get_user(user_id)
        
        if not user:
            bot.send_message(user_id, "❌ প্রথমে /start দিন")
            return
        
        if user['is_banned'] == 1:
            bot.send_message(user_id, "🚫 আপনি ব্যান করেছেন!")
            return
        
        # ডেইলি লিমিট চেক
        conn = get_db()
        if conn:
            today_tasks = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND DATE(created_at, 'unixepoch') = DATE('now')",
                (user_id,)
            ).fetchone()[0]
            conn.close()
            
            if today_tasks >= 50:
                bot.send_message(user_id, "📊 আজকে ৫০ টি টাস্ক সম্পন্ন করেছেন! কাল আবার চেষ্টা করুন।")
                return
        
        reward = float(get_setting('per_task_reward') or 0.10)
        wait_time = int(get_setting('min_wait_seconds') or 15)
        server_url = get_setting('server_url').rstrip('/')
        
        # অ্যাড ফেচ
        ad_data = get_adexium_ad(user_id, user['name'])
        
        ad_url = ad_data.get('clickUrl', 'https://t.me')
        ad_image = ad_data.get('image')
        ad_text = html.escape(ad_data.get('text', 'Sponsored Ad'))
        button_text = ad_data.get('buttonText', 'Go!')
        
        # Token তৈরি
        token = f"{user_id}_{uuid.uuid4().hex[:10]}"
        
        conn = get_db()
        if conn:
            conn.execute(
                'INSERT INTO tasks (token, user_id, ad_url, created_at) VALUES (?, ?, ?, ?)',
                (token, user_id, ad_url, time.time())
            )
            conn.commit()
            conn.close()
        
        track_link = f"{server_url}/click/{token}"
        
        # Inline Keyboard
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton(f"🔗 {button_text} (+৳{reward:.2f})", url=track_link),
            types.InlineKeyboardButton("✅ Verify & Claim", callback_data=f"verify_{token}")
        )
        
        task_text = f"""
🎯 <b>Sponsored Task</b>
━━━━━━━━━━━━━━━━━━
📢 {ad_text}

💰 <b>Reward:</b> ৳ {reward:.2f}
⏳ <b>Wait:</b> {wait_time} seconds

📌 <b>How to complete:</b>
1️⃣ Click the link above
2️⃣ Wait {wait_time} seconds
3️⃣ Click "Verify & Claim"

⚠️ Don't close the ad window!
"""
        
        # অ্যাড ইমেজ সহ পাঠান
        if ad_image and ad_image.startswith('http'):
            try:
                bot.send_photo(
                    user_id,
                    ad_image,
                    caption=task_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except:
                bot.send_message(
                    user_id,
                    task_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        else:
            bot.send_message(
                user_id,
                task_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
        logger.info(f"✅ Task sent to {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Task error: {e}")
        bot.send_message(message.chat.id, "❌ সমস্যা হয়েছে! আবার চেষ্টা করুন।")

# ================= VERIFY ================= #
@bot.callback_query_handler(func=lambda call: call.data.startswith("verify_"))
def verify_callback(call):
    try:
        token = call.data.replace("verify_", "")
        user_id = call.from_user.id
        
        conn = get_db()
        if not conn:
            bot.answer_callback_query(call.id, "❌ ডেটাবেস সমস্যা!", show_alert=True)
            return
        
        task = conn.execute(
            'SELECT * FROM tasks WHERE token = ? AND user_id = ?',
            (token, user_id)
        ).fetchone()
        
        if not task:
            conn.close()
            bot.answer_callback_query(call.id, "❌ টাস্ক পাওয়া যায়নি!", show_alert=True)
            return
        
        if task['is_claimed'] == 1:
            conn.close()
            bot.answer_callback_query(call.id, "⚠️ ইতিমধ্যে ক্লেইম করা হয়েছে!", show_alert=True)
            return
        
        if task['is_visited'] == 0:
            conn.close()
            bot.answer_callback_query(
                call.id,
                "❌ প্রথমে লিংকে ক্লিক করুন!\nতারপর Verify দিন।",
                show_alert=True
            )
            return
        
        wait_time = int(get_setting('min_wait_seconds') or 15)
        time_spent = time.time() - float(task['created_at'])
        
        if time_spent < wait_time:
            conn.close()
            remaining = int(wait_time - time_spent)
            bot.answer_callback_query(
                call.id,
                f"⏳ আরও {remaining} সেকেন্ড অপেক্ষা করুন!",
                show_alert=True
            )
            return
        
        # ✅ সফল - টাকা যোগ করুন
        reward = float(get_setting('per_task_reward') or 0.10)
        
        conn.execute('UPDATE tasks SET is_claimed = 1 WHERE token = ?', (token,))
        conn.execute(
            'UPDATE users SET balance = balance + ?, total_tasks = total_tasks + 1 WHERE user_id = ?',
            (reward, user_id)
        )
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(
            call.id,
            f"✅ সফল! +৳{reward:.2f} টাকা যোগ হয়েছে!",
            show_alert=True
        )
        
        # মেসেজ আপডেট
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"✅ <b>Task Completed!</b>\n💰 +৳{reward:.2f} Added",
                parse_mode="HTML"
            )
        except:
            try:
                bot.edit_message_text(
                    f"✅ <b>Task Completed!</b>\n💰 +৳{reward:.2f} Added",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML"
                )
            except:
                pass
                
        logger.info(f"✅ Task completed: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Verify error: {e}")
        bot.answer_callback_query(call.id, "❌ ভেরিফিকেশন ব্যর্থ!", show_alert=True)

# ================= BALANCE ================= #
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance_command(message):
    try:
        user = get_user(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "❌ /start দিন")
            return
        
        text = f"""
💰 <b>Your Balance</b>
━━━━━━━━━━━━━━━━━━
💵 Balance: ৳ <b>{user['balance']:.2f}</b>
🎯 Tasks Done: {user['total_tasks']}
👥 Total Refers: {user['total_refers'] or 0}
"""
        bot.send_message(message.chat.id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ Balance error: {e}")

# ================= REFER ================= #
@bot.message_handler(func=lambda m: m.text == "👥 Refer")
def refer_command(message):
    try:
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={message.from_user.id}"
        
        text = f"""
👥 <b>Refer & Earn</b>
━━━━━━━━━━━━━━━━━━
🎁 <b>10% lifetime commission!</b>

🔗 <b>Your Refer Link:</b>
<code>{ref_link}</code>

📤 Share this link with friends!
When they complete tasks, you earn 10%!
"""
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "📤 Share",
                url=f"https://t.me/share/url?url={ref_link}&text=Join%20Easy%20Earn%20Bot%20and%20earn%20free%20money!"
            )
        )
        bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ Refer error: {e}")

# ================= WITHDRAW ================= #
@bot.message_handler(func=lambda m: m.text == "💳 Withdraw")
def withdraw_command(message):
    try:
        user = get_user(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "❌ /start দিন")
            return
        
        min_withdraw = float(get_setting('min_withdraw') or 20)
        
        if user['balance'] < min_withdraw:
            bot.send_message(
                message.chat.id,
                f"❌ Minimum withdraw: ৳{min_withdraw}\n"
                f"Your balance: ৳{user['balance']:.2f}",
                parse_mode="HTML"
            )
            return
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("🔴 bKash", callback_data="withdraw_bKash"),
            types.InlineKeyboardButton("🟠 Nagad", callback_data="withdraw_Nagad")
        )
        bot.send_message(
            message.chat.id,
            "💳 <b>Select Payment Method:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Withdraw error: {e}")

# ================= MY ACCOUNT ================= #
@bot.message_handler(func=lambda m: m.text == "👤 My Account")
def account_command(message):
    try:
        user = get_user(message.from_user.id)
        if not user:
            bot.send_message(message.chat.id, "❌ /start দিন")
            return
        
        text = f"""
👤 <b>My Account</b>
━━━━━━━━━━━━━━━━━━
🔖 Name: {html.escape(user['name'])}
🆔 ID: <code>{user['user_id']}</code>
💰 Balance: ৳ <b>{user['balance']:.2f}</b>
🎯 Tasks Done: {user['total_tasks']}
👥 Total Refers: {user['total_refers'] or 0}
📅 Joined: {user['joined_at']}
"""
        bot.send_message(message.chat.id, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ Account error: {e}")

# ================= SUPPORT ================= #
@bot.message_handler(func=lambda m: m.text == "🛠 Support")
def support_command(message):
    bot.send_message(
        message.chat.id,
        f"📞 <b>Support</b>\n\n"
        f"Contact: {SUPPORT_USERNAME}\n"
        f"Channel: @onlysazzat\n\n"
        f"🤖 Bot Version: v2.0",
        parse_mode="HTML"
    )

# ================= WITHDRAW CALLBACK ================= #
@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_"))
def withdraw_method(call):
    try:
        method = call.data.replace("withdraw_", "")
        user_id = call.from_user.id
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        msg = bot.send_message(
            user_id,
            f"💵 <b>{method}</b> selected.\n\n"
            f"📝 Enter amount (min: ৳{get_setting('min_withdraw')}):",
            parse_mode="HTML"
        )
        
        # স্টেপ বাই স্টেপ ডেটা সংরক্ষণ
        bot.register_next_step_handler(msg, process_withdraw_amount, method, user_id)
        
    except Exception as e:
        logger.error(f"❌ Withdraw callback error: {e}")

def process_withdraw_amount(message, method, user_id):
    try:
        amount = float(message.text.strip())
        min_withdraw = float(get_setting('min_withdraw') or 20)
        user = get_user(user_id)
        
        if amount < min_withdraw:
            bot.send_message(user_id, f"❌ Minimum {min_withdraw} টাকা দিন।")
            return
        
        if amount > user['balance']:
            bot.send_message(user_id, f"❌ আপনার ব্যালেন্স: ৳{user['balance']:.2f}")
            return
        
        msg = bot.send_message(
            user_id,
            f"📱 Enter your {method} number:",
            parse_mode="HTML"
        )
        
        bot.register_next_step_handler(msg, process_withdraw_number, method, user_id, amount)
        
    except:
        bot.send_message(user_id, "❌ সঠিক সংখ্যা দিন।")

def process_withdraw_number(message, method, user_id, amount):
    try:
        number = message.text.strip()
        
        if len(number) < 11:
            bot.send_message(user_id, "❌ সঠিক ১১ ডিজিটের নম্বর দিন।")
            return
        
        # ডেটাবেসে সেভ
        conn = get_db()
        if conn:
            conn.execute(
                'INSERT INTO withdrawals (user_id, amount, method, number, status) VALUES (?, ?, ?, ?, ?)',
                (user_id, amount, method, number, 'pending')
            )
            conn.commit()
            conn.close()
        
        # ব্যালেন্স কমানো
        conn = get_db()
        if conn:
            conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
            conn.commit()
            conn.close()
        
        bot.send_message(
            user_id,
            f"✅ <b>Withdraw Request Submitted!</b>\n\n"
            f"💰 Amount: ৳{amount:.2f}\n"
            f"💳 Method: {method}\n"
            f"📱 Number: {number}\n\n"
            "⏳ Wait for admin approval.",
            parse_mode="HTML"
        )
        
        # অ্যাডমিনকে জানান
        admin_text = f"""
💸 <b>New Withdraw Request</b>
━━━━━━━━━━━━━━━━━━
👤 User: {user_id}
💰 Amount: ৳{amount:.2f}
💳 Method: {method}
📱 Number: {number}
"""
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, admin_text, parse_mode="HTML")
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ Withdraw number error: {e}")

# ================= ADMIN COMMANDS ================= #
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💸 Withdrawals", callback_data="admin_withdrawals")
    )
    bot.send_message(message.chat.id, "👑 Admin Panel", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    if call.data == "admin_stats":
        conn = get_db()
        if conn:
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_tasks = conn.execute("SELECT SUM(total_tasks) FROM users").fetchone()[0] or 0
            total_balance = conn.execute("SELECT SUM(balance) FROM users").fetchone()[0] or 0
            pending_withdraw = conn.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'").fetchone()[0]
            conn.close()
            
            text = f"""
📊 <b>Bot Statistics</b>
━━━━━━━━━━━━━━━━━━
👥 Total Users: {total_users}
🎯 Total Tasks: {total_tasks}
💰 Total Balance: ৳{total_balance:.2f}
⏳ Pending Withdrawals: {pending_withdraw}
"""
            bot.send_message(call.message.chat.id, text, parse_mode="HTML")
    
    elif call.data == "admin_settings":
        text = f"""
⚙️ <b>Current Settings</b>
━━━━━━━━━━━━━━━━━━
1️⃣ Reward: ৳{get_setting('per_task_reward')}
2️⃣ Min Withdraw: ৳{get_setting('min_withdraw')}
3️⃣ Wait Time: {get_setting('min_wait_seconds')}s
4️⃣ Commission: {get_setting('refer_commission')}%
5️⃣ WID: <code>{get_setting('adexium_wid')}</code>

<b>Commands to change:</b>
/setreward 0.20
/setmin 30
/settime 20
/setwid <new_wid>
"""
        bot.send_message(call.message.chat.id, text, parse_mode="HTML")
    
    elif call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast)
    
    elif call.data == "admin_withdrawals":
        conn = get_db()
        if conn:
            pending = conn.execute(
                "SELECT * FROM withdrawals WHERE status='pending' ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
            conn.close()
            
            if not pending:
                bot.send_message(call.message.chat.id, "✅ No pending withdrawals")
                return
            
            text = "💸 <b>Pending Withdrawals:</b>\n\n"
            for w in pending:
                text += f"ID: #{w['id']} | User: {w['user_id']} | ৳{w['amount']} | {w['method']}\n"
            
            bot.send_message(call.message.chat.id, text, parse_mode="HTML")

def process_broadcast(message):
    text = message.text
    conn = get_db()
    if conn:
        users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
        conn.close()
        
        sent = 0
        for user in users:
            try:
                bot.send_message(user['user_id'], f"📢 <b>Announcement</b>\n\n{html.escape(text)}", parse_mode="HTML")
                sent += 1
                time.sleep(0.05)
            except:
                pass
        
        bot.send_message(message.chat.id, f"✅ Broadcast sent to {sent} users")

# ================= ADMIN SET COMMANDS ================= #
@bot.message_handler(commands=['setreward'])
def set_reward(message):
    if message.from_user.id in ADMIN_IDS:
        try:
            value = float(message.text.split()[1])
            conn = get_db()
            if conn:
                conn.execute("UPDATE settings SET value=? WHERE key='per_task_reward'", (str(value),))
                conn.commit()
                conn.close()
            bot.send_message(message.chat.id, f"✅ Reward set to ৳{value:.2f}")
        except:
            bot.send_message(message.chat.id, "❌ /setreward 0.10")

@bot.message_handler(commands=['setmin'])
def set_min(message):
    if message.from_user.id in ADMIN_IDS:
        try:
            value = float(message.text.split()[1])
            conn = get_db()
            if conn:
                conn.execute("UPDATE settings SET value=? WHERE key='min_withdraw'", (str(value),))
                conn.commit()
                conn.close()
            bot.send_message(message.chat.id, f"✅ Min withdraw set to ৳{value:.2f}")
        except:
            bot.send_message(message.chat.id, "❌ /setmin 20")

@bot.message_handler(commands=['settime'])
def set_time(message):
    if message.from_user.id in ADMIN_IDS:
        try:
            value = int(message.text.split()[1])
            conn = get_db()
            if conn:
                conn.execute("UPDATE settings SET value=? WHERE key='min_wait_seconds'", (str(value),))
                conn.commit()
                conn.close()
            bot.send_message(message.chat.id, f"✅ Wait time set to {value}s")
        except:
            bot.send_message(message.chat.id, "❌ /settime 15")

@bot.message_handler(commands=['setwid'])
def set_wid(message):
    if message.from_user.id in ADMIN_IDS:
        try:
            value = message.text.split()[1]
            conn = get_db()
            if conn:
                conn.execute("UPDATE settings SET value=? WHERE key='adexium_wid'", (value,))
                conn.commit()
                conn.close()
            bot.send_message(message.chat.id, f"✅ WID updated: <code>{value}</code>", parse_mode="HTML")
        except:
            bot.send_message(message.chat.id, "❌ /setwid <your_wid>")

# ================= MAIN ================= #
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Easy Earn Bot Starting...")
    print(f"📡 Server: http://localhost:{PORT}")
    print(f"🎯 WID: {ADEXIUM_WID}")
    print("=" * 50)
    
    try:
        bot.infinity_polling(timeout=30, skip_pending=True)
    except Exception as e:
        print(f"❌ Bot Error: {e}")
        time.sleep(5)
