import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time

# ================================================================
# কনফিগারেশন
# ================================================================
BOT_TOKEN = "8779887718:AAGUJEzRGhXl-W6BhnuRrfYeYsr245dc8Zo"
ADMIN_IDS = [8876911955]
WID = "f6dc8ad8-0b3e-48a3-94a1-da6b3b7aec1f"

bot = telebot.TeleBot(BOT_TOKEN)

# ================================================================
# ইউজার ডেটা (সিম্পল ডিকশনারি)
# ================================================================
users = {}
user_tasks = {}

# ================================================================
# Adexium থেকে অ্যাড আনা
# ================================================================
def get_ad():
    """Adexium থেকে অ্যাড ডেটা আনো"""
    try:
        url = "https://bid.tgads.live/bot-request"
        headers = {"Content-Type": "application/json"}
        data = {
            "wid": WID,
            "language": "bn",
            "isPremium": False,
            "firstName": "User",
            "telegramId": "123"
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"API Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"API Response: {result}")
            return result
        else:
            print(f"API Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

# ================================================================
# /start কমান্ড
# ================================================================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    
    if user_id not in users:
        users[user_id] = {'balance': 0, 'clicks': 0}
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📋 টাস্ক নিন", callback_data="task"),
        InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance")
    )
    
    bot.reply_to(
        message,
        f"👋 স্বাগতম! আপনার ব্যালেন্স: {users[user_id]['balance']} টাকা",
        reply_markup=markup
    )

# ================================================================
# /task কমান্ড
# ================================================================
@bot.message_handler(commands=['task'])
def task_command(message):
    user_id = message.from_user.id
    
    # Adexium থেকে অ্যাড আনুন
    ad_data = get_ad()
    
    if ad_data and ad_data.get('id'):
        # আসল অ্যাড
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                ad_data.get('buttonText', 'Go!'),
                url=ad_data.get('clickUrl', 'https://go.tgads.live/click')
            )
        )
        markup.add(
            InlineKeyboardButton("✅ ক্লিক সম্পন্ন", callback_data=f"done_{ad_data.get('id')}")
        )
        
        if ad_data.get('image'):
            bot.send_photo(
                message.chat.id,
                photo=ad_data.get('image'),
                caption=f"📢 {ad_data.get('text', 'অ্যাড দেখুন!')}\n\n💰 পুরস্কার: ১.০০ টাকা",
                reply_markup=markup
            )
        else:
            bot.send_message(
                message.chat.id,
                f"📢 {ad_data.get('text', 'অ্যাড দেখুন!')}\n\n💰 পুরস্কার: ১.০০ টাকা",
                reply_markup=markup
            )
        
        user_tasks[user_id] = ad_data.get('id')
    else:
        # ডেমো অ্যাড (API কাজ না করলে)
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔗 ভিজিট করুন", url="https://google.com"),
            InlineKeyboardButton("✅ ক্লিক সম্পন্ন", callback_data="done_demo")
        )
        
        bot.send_photo(
            message.chat.id,
            photo="https://via.placeholder.com/400x250/1a1a2e/ffd700?text=Watch+Ad",
            caption="📢 ডেমো অ্যাড!\n\n💰 পুরস্কার: ১.০০ টাকা",
            reply_markup=markup
        )
        user_tasks[user_id] = "demo"

# ================================================================
# /balance কমান্ড
# ================================================================
@bot.message_handler(commands=['balance'])
def balance_command(message):
    user_id = message.from_user.id
    balance = users.get(user_id, {}).get('balance', 0)
    bot.reply_to(message, f"💰 আপনার ব্যালেন্স: {balance:.2f} টাকা")

# ================================================================
# কলব্যাক হ্যান্ডলার
# ================================================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    
    if data == "task":
        task_command(call.message)
        bot.answer_callback_query(call.id)
    
    elif data == "balance":
        balance_command(call.message)
        bot.answer_callback_query(call.id)
    
    elif data == "done_demo" or data.startswith("done_"):
        # টাকা যোগ করুন
        if user_id not in users:
            users[user_id] = {'balance': 0, 'clicks': 0}
        
        users[user_id]['balance'] = users[user_id].get('balance', 0) + 1
        users[user_id]['clicks'] = users[user_id].get('clicks', 0) + 1
        
        bot.edit_message_caption(
            f"✅ ক্লিক সম্পন্ন!\n\n💰 ১ টাকা পেয়েছেন!\n💵 নতুন ব্যালেন্স: {users[user_id]['balance']:.2f} টাকা",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id, "🎉 ১ টাকা পেয়েছেন!")

# ================================================================
# /admin কমান্ড
# ================================================================
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ অ্যাডমিন নন!")
        return
    
    total = len(users)
    total_balance = sum(u.get('balance', 0) for u in users.values())
    
    bot.reply_to(
        message,
        f"📊 *পরিসংখ্যান*\n━━━━━━━━━━━━━━━━\n"
        f"👥 মোট ইউজার: {total}\n"
        f"💰 মোট ব্যালেন্স: {total_balance:.2f} টাকা",
        parse_mode='Markdown'
    )

# ================================================================
# বট চালু
# ================================================================
print("🤖 বট চালু হচ্ছে...")
print(f"👤 অ্যাডমিন: {ADMIN_IDS}")
print(f"📋 Widget: {WID}")

while True:
    try:
        bot.polling(none_stop=True, interval=1)
    except Exception as e:
        print(f"⚠️ এরর: {e}")
        time.sleep(5)
