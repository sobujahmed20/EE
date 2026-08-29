import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import time
import os
from datetime import datetime

# ================================================================
# কনফিগারেশন (এখানে আপনার তথ্য দিন)
# ================================================================
BOT_TOKEN = "8779887718:AAGUJEzRGhXl-W6BhnuRrfYeYsr245dc8Zo"
ADMIN_IDS = [8876911955]  # আপনার টেলিগ্রাম আইডি দিন
WID = "f6dc8ad8-0b3e-48a3-94a1-da6b3b7aec1f"  # আপনার Widget ID

bot = telebot.TeleBot(BOT_TOKEN)

# ================================================================
# ডেটা স্টোর (ইউজার ডেটা)
# ================================================================
users = {}
user_tasks = {}

# ================================================================
# Adexium থেকে অ্যাড আনা
# ================================================================
def get_adexium_ad(telegram_id, first_name, is_premium=False):
    """Adexium API থেকে অ্যাড ডেটা আনো"""
    try:
        url = "https://bid.tgads.live/bot-request"
        headers = {"Content-Type": "application/json"}
        data = {
            "wid": WID,
            "language": "bn",
            "isPremium": is_premium,
            "firstName": first_name,
            "telegramId": str(telegram_id)
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

# ================================================================
# ইউজারকে অ্যাড পাঠানো
# ================================================================
def send_ad_to_user(chat_id, ad_data):
    """ইউজারকে অ্যাড পাঠাও"""
    if not ad_data:
        bot.send_message(chat_id, "⏳ কোনো অ্যাড নেই। কিছুক্ষণ পর চেষ্টা করুন।")
        return None
    
    # কীবোর্ড তৈরি
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            ad_data.get('buttonText', '🔗 ক্লিক করুন'),
            url=ad_data.get('clickUrl', 'https://go.tgads.live/click')
        )
    )
    markup.add(
        InlineKeyboardButton("✅ ক্লিক সম্পন্ন", callback_data=f"done_{ad_data.get('id', '')}")
    )
    
    # অ্যাড পাঠান
    try:
        if ad_data.get('image'):
            bot.send_photo(
                chat_id,
                photo=ad_data.get('image'),
                caption=f"📢 {ad_data.get('text', 'নতুন অ্যাড দেখুন!')}\n\n💰 পুরস্কার: ১.০০ টাকা\n⏳ অ্যাড দেখে ১০ সেকেন্ড পর 'ক্লিক সম্পন্ন' চাপুন।",
                reply_markup=markup
            )
        else:
            bot.send_message(
                chat_id,
                f"📢 {ad_data.get('text', 'নতুন অ্যাড দেখুন!')}\n\n💰 পুরস্কার: ১.০০ টাকা\n🔗 নিচের লিংকে ক্লিক করুন:",
                reply_markup=markup
            )
        return ad_data.get('id')
    except Exception as e:
        print(f"Send error: {e}")
        return None

# ================================================================
# স্টার্ট কমান্ড
# ================================================================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # ইউজার সেভ
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'total_clicks': 0,
            'first_name': first_name,
            'joined_at': str(datetime.now()),
            'is_banned': False
        }
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📋 টাস্ক নিন", callback_data="task"),
        InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance"),
        InlineKeyboardButton("💳 উইথড্র", callback_data="withdraw"),
        InlineKeyboardButton("👤 প্রোফাইল", callback_data="profile")
    )
    
    bot.send_message(
        message.chat.id,
        f"👋 স্বাগতম {first_name}!\n\n"
        "💰 এই বটের মাধ্যমে আপনি অ্যাড দেখে টাকা আয় করতে পারবেন।\n\n"
        "📌 'টাস্ক নিন' এ ক্লিক করে শুরু করুন!",
        reply_markup=markup
    )

# ================================================================
# টাস্ক কমান্ড
# ================================================================
@bot.message_handler(commands=['task'])
def task_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # চেক করুন ইউজার ব্লক কিনা
    if users.get(user_id, {}).get('is_banned', False):
        bot.reply_to(message, "🚫 আপনার অ্যাকাউন্ট ব্লক করা হয়েছে!")
        return
    
    # অ্যাড ডেটা আনুন
    ad_data = get_adexium_ad(user_id, first_name)
    
    if ad_data:
        task_id = send_ad_to_user(message.chat.id, ad_data)
        if task_id:
            user_tasks[user_id] = {
                'task_id': task_id,
                'ad_data': ad_data,
                'timestamp': time.time()
            }
    else:
        bot.reply_to(message, "⏳ কোনো অ্যাড নেই। কিছুক্ষণ পর চেষ্টা করুন।")

# ================================================================
# ব্যালেন্স কমান্ড
# ================================================================
@bot.message_handler(commands=['balance'])
def balance_command(message):
    user_id = message.from_user.id
    user_data = users.get(user_id, {})
    balance = user_data.get('balance', 0)
    clicks = user_data.get('total_clicks', 0)
    
    bot.reply_to(
        message,
        f"💰 *আপনার ব্যালেন্স*\n━━━━━━━━━━━━━━━━\n"
        f"💵 ব্যালেন্স: {balance:.2f} টাকা\n"
        f"🖱️ মোট ক্লিক: {clicks}\n\n"
        f"💡 ন্যূনতম ৫০ টাকা তোলা যাবে।",
        parse_mode='Markdown'
    )

# ================================================================
# উইথড্র কমান্ড
# ================================================================
@bot.message_handler(commands=['withdraw'])
def withdraw_command(message):
    user_id = message.from_user.id
    user_data = users.get(user_id, {})
    balance = user_data.get('balance', 0)
    
    if balance < 50:
        bot.reply_to(
            message,
            f"⚠️ আপনার ব্যালেন্স {balance:.2f} টাকা।\n"
            f"ন্যূনতম ৫০ টাকা তোলা যাবে। আরও {50 - balance:.2f} টাকা প্রয়োজন।"
        )
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💳 বিকাশ", callback_data="wd_bkash"),
        InlineKeyboardButton("💳 নগদ", callback_data="wd_nagad"),
        InlineKeyboardButton("💳 রকেট", callback_data="wd_rocket")
    )
    
    bot.reply_to(
        message,
        f"💰 আপনার ব্যালেন্স: {balance:.2f} টাকা\n\n"
        "পেমেন্ট মেথড সিলেক্ট করুন:",
        reply_markup=markup
    )

# ================================================================
# হেল্প কমান্ড
# ================================================================
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(
        message,
        "📖 *সাহায্য*\n━━━━━━━━━━━━━━━━\n\n"
        "🔹 `/start` - বট চালু করুন\n"
        "🔹 `/task` - নতুন টাস্ক নিন\n"
        "🔹 `/balance` - ব্যালেন্স দেখুন\n"
        "🔹 `/withdraw` - টাকা তোলার অনুরোধ করুন\n"
        "🔹 `/help` - এই মেসেজ দেখুন\n\n"
        "📌 প্রতি ক্লিকে পাবেন ১.০০ টাকা\n"
        "💰 ন্যূনতম উইথড্র: ৫০ টাকা",
        parse_mode='Markdown'
    )

# ================================================================
# অ্যাডমিন কমান্ড
# ================================================================
@bot.message_handler(commands=['admin'])
def admin_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ আপনি অ্যাডমিন নন!")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 সব ইউজার", callback_data="admin_users"),
        InlineKeyboardButton("💰 ব্যালেন্স যোগ", callback_data="admin_add_balance"),
        InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="admin_broadcast"),
        InlineKeyboardButton("🚫 ব্লক/আনব্লক", callback_data="admin_block"),
        InlineKeyboardButton("📊 পরিসংখ্যান", callback_data="admin_stats"),
        InlineKeyboardButton("💳 উইথড্র লিস্ট", callback_data="admin_withdraws")
    )
    
    bot.send_message(
        message.chat.id,
        "🔐 *অ্যাডমিন প্যানেল*\n━━━━━━━━━━━━━━━━\nনিচের অপশন থেকে নির্বাচন করুন:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ================================================================
# অ্যাডমিন ব্যালেন্স যোগ কমান্ড
# ================================================================
@bot.message_handler(commands=['addbalance'])
def add_balance_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ অ্যাডমিন নন!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ ফরম্যাট: `/addbalance [user_id] [amount]`")
            return
        
        target_id = int(parts[1])
        amount = float(parts[2])
        
        if target_id not in users:
            bot.reply_to(message, f"❌ ইউজার {target_id} খুঁজে পাওয়া যায়নি!")
            return
        
        users[target_id]['balance'] = users[target_id].get('balance', 0) + amount
        bot.reply_to(
            message,
            f"✅ ইউজার `{target_id}`-এর ব্যালেন্সে {amount:.2f} টাকা যোগ হয়েছে!\n"
            f"নতুন ব্যালেন্স: {users[target_id]['balance']:.2f} টাকা",
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {e}")

# ================================================================
# অ্যাডমিন ব্লক কমান্ড
# ================================================================
@bot.message_handler(commands=['block'])
def block_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ অ্যাডমিন নন!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ ফরম্যাট: `/block [user_id]`")
            return
        
        target_id = int(parts[1])
        
        if target_id not in users:
            bot.reply_to(message, f"❌ ইউজার {target_id} খুঁজে পাওয়া যায়নি!")
            return
        
        users[target_id]['is_banned'] = True
        bot.reply_to(message, f"✅ ইউজার `{target_id}` ব্লক করা হয়েছে!", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {e}")

# ================================================================
# অ্যাডমিন আনব্লক কমান্ড
# ================================================================
@bot.message_handler(commands=['unblock'])
def unblock_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ অ্যাডমিন নন!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ ফরম্যাট: `/unblock [user_id]`")
            return
        
        target_id = int(parts[1])
        
        if target_id not in users:
            bot.reply_to(message, f"❌ ইউজার {target_id} খুঁজে পাওয়া যায়নি!")
            return
        
        users[target_id]['is_banned'] = False
        bot.reply_to(message, f"✅ ইউজার `{target_id}` আনব্লক করা হয়েছে!", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {e}")

# ================================================================
# অ্যাডমিন ব্রডকাস্ট কমান্ড
# ================================================================
@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ অ্যাডমিন নন!")
        return
    
    try:
        msg = message.text.replace('/broadcast', '').strip()
        if not msg:
            bot.reply_to(message, "❌ মেসেজ লিখুন!")
            return
        
        count = 0
        for uid in users.keys():
            try:
                bot.send_message(uid, f"📢 *ব্রডকাস্ট*\n━━━━━━━━━━━━━━━━\n\n{msg}", parse_mode='Markdown')
                count += 1
                time.sleep(0.05)
            except:
                pass
        
        bot.reply_to(message, f"📢 ব্রডকাস্ট সম্পন্ন!\n{count} জন ইউজারকে মেসেজ পাঠানো হয়েছে।")
    except Exception as e:
        bot.reply_to(message, f"❌ এরর: {e}")

# ================================================================
# কলব্যাক হ্যান্ডলার
# ================================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    # ===== টাস্ক =====
    if data == "task":
        task_command(call.message)
        bot.answer_callback_query(call.id)
    
    # ===== ব্যালেন্স =====
    elif data == "balance":
        balance_command(call.message)
        bot.answer_callback_query(call.id)
    
    # ===== উইথড্র =====
    elif data == "withdraw":
        withdraw_command(call.message)
        bot.answer_callback_query(call.id)
    
    # ===== প্রোফাইল =====
    elif data == "profile":
        user_data = users.get(user_id, {})
        bot.edit_message_text(
            f"👤 *প্রোফাইল*\n━━━━━━━━━━━━━━━━\n"
            f"🆔 আইডি: {user_id}\n"
            f"👤 নাম: {user_data.get('first_name', 'N/A')}\n"
            f"💰 ব্যালেন্স: {user_data.get('balance', 0):.2f} টাকা\n"
            f"🖱️ ক্লিক: {user_data.get('total_clicks', 0)}\n"
            f"📅 যোগদান: {user_data.get('joined_at', 'N/A')}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    # ===== ক্লিক সম্পন্ন =====
    elif data.startswith("done_"):
        task_id = data.replace("done_", "")
        
        if user_id in user_tasks:
            task_data = user_tasks[user_id]
            if task_data.get('task_id') == task_id:
                users[user_id]['balance'] = users[user_id].get('balance', 0) + 1.0
                users[user_id]['total_clicks'] = users[user_id].get('total_clicks', 0) + 1
                del user_tasks[user_id]
                
                bot.edit_message_caption(
                    f"✅ *ক্লিক সম্পন্ন!*\n\n"
                    f"💰 ১.০০ টাকা আপনার অ্যাকাউন্টে যোগ হয়েছে!\n"
                    f"💵 নতুন ব্যালেন্স: {users[user_id]['balance']:.2f} টাকা",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                bot.answer_callback_query(call.id, "🎉 ১ টাকা পেয়েছেন!")
            else:
                bot.answer_callback_query(call.id, "⚠️ এই টাস্ক আগে সম্পন্ন হয়েছে!")
        else:
            bot.answer_callback_query(call.id, "⏳ কোন টাস্ক নেই!")
    
    # ===== উইথড্র মেথড =====
    elif data.startswith("wd_"):
        method = data.replace("wd_", "")
        method_names = {"bkash": "বিকাশ", "nagad": "নগদ", "rocket": "রকেট"}
        method_name = method_names.get(method, method)
        
        user_data = users.get(user_id, {})
        balance = user_data.get('balance', 0)
        
        if balance >= 50:
            bot.edit_message_text(
                f"✅ *উইথড্র অনুরোধ গ্রহণ করা হয়েছে!*\n\n"
                f"💳 মেথড: {method_name}\n"
                f"💰 পরিমাণ: {balance:.2f} টাকা\n"
                f"⏳ অ্যাডমিন অ্যাপ্রুভ করলে টাকা পাঠানো হবে।",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(
                        admin_id,
                        f"💳 *নতুন উইথড্র রিকোয়েস্ট*\n"
                        f"👤 ইউজার: {user_id}\n"
                        f"💳 মেথড: {method_name}\n"
                        f"💰 পরিমাণ: {balance:.2f} টাকা",
                        parse_mode='Markdown'
                    )
                except:
                    pass
        else:
            bot.answer_callback_query(call.id, f"⚠️ ব্যালেন্স কম! {50 - balance:.2f} টাকা প্রয়োজন।")
    
    # ===== অ্যাডমিন কলব্যাক =====
    elif data == "admin_users":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ অ্যাডমিন নন!")
            return
        
        total = len(users)
        active = sum(1 for u in users.values() if u.get('total_clicks', 0) > 0)
        
        text = f"👥 *সব ইউজার*\n━━━━━━━━━━━━━━━━\n"
        text += f"📊 মোট ইউজার: {total}\n"
        text += f"🟢 সক্রিয়: {active}\n"
        text += f"🔴 নিষ্ক্রিয়: {total - active}\n━━━━━━━━━━━━━━━━\n\n"
        
        for i, (uid, data) in enumerate(list(users.items())[:10], 1):
            text += f"{i}. {data.get('first_name', 'N/A')} — {data.get('balance', 0):.2f} টাকা\n"
        
        if total > 10:
            text += f"\n... এবং আরও {total - 10} জন"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif data == "admin_stats":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ অ্যাডমিন নন!")
            return
        
        total = len(users)
        total_balance = sum(u.get('balance', 0) for u in users.values())
        total_clicks = sum(u.get('total_clicks', 0) for u in users.values())
        
        text = f"📊 *প্ল্যাটফর্ম পরিসংখ্যান*\n━━━━━━━━━━━━━━━━\n"
        text += f"👥 মোট ইউজার: {total}\n"
        text += f"💰 মোট ব্যালেন্স: {total_balance:.2f} টাকা\n"
        text += f"🖱️ মোট ক্লিক: {total_clicks}\n"
        text += f"📈 গড় ক্লিক/ইউজার: {total_clicks/total if total > 0 else 0:.1f}"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif data == "admin_add_balance":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ অ্যাডমিন নন!")
            return
        
        bot.edit_message_text(
            "💰 *ব্যালেন্স যোগ করুন*\n\n"
            "ফরম্যাট: `/addbalance [ইউজার_আইডি] [টাকা]`\n\n"
            "যেমন: `/addbalance 123456789 50`",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif data == "admin_broadcast":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ অ্যাডমিন নন!")
            return
        
        bot.edit_message_text(
            "📢 *ব্রডকাস্ট*\n\n"
            "সব ইউজারকে মেসেজ পাঠাতে `/broadcast [মেসেজ]` লিখুন।\n\n"
            "যেমন: `/broadcast নতুন আপডেট এসেছে!`",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif data == "admin_block":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ অ্যাডমিন নন!")
            return
        
        bot.edit_message_text(
            "🚫 *ব্লক/আনব্লক*\n\n"
            "ব্লক করতে: `/block [ইউজার_আইডি]`\n"
            "আনব্লক করতে: `/unblock [ইউজার_আইডি]`\n\n"
            "যেমন: `/block 123456789`",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif data == "admin_withdraws":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⛔ অ্যাডমিন নন!")
            return
        
        bot.edit_message_text(
            "💳 *উইথড্র রিকোয়েস্ট*\n\n"
            "এখানে পেন্ডিং রিকোয়েস্ট দেখাবে।\n"
            "(ডাটাবেজ কানেক্ট করলে রিয়েল ডেটা আসবে)",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    else:
        bot.answer_callback_query(call.id)

# ================================================================
# বট চালু করা
# ================================================================
if __name__ == "__main__":
    print("🤖 বট চালু হচ্ছে...")
    print(f"👤 অ্যাডমিন আইডি: {ADMIN_IDS}")
    print(f"📋 Widget ID: {WID}")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            print(f"⚠️ এরর: {e}")
            time.sleep(5)
