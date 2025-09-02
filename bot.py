import telebot
from telebot import types
import threading
import time
import random
import json
import os

# ---------------------------------------------------------------------------
# >>  اینجا توکن ربات خود را که از BotFather گرفته‌اید، قرار دهید <<
TOKEN = "YOUR_BOT_TOKEN_HERE"
# ---------------------------------------------------------------------------

# >> مسیر ذخیره فایل وضعیت برای سرویس Render <<
# Render فایل‌ها را در حافظه موقت ذخیره می‌کند. برای ذخیره دائمی،
# باید از مسیری که در بخش Disks تعریف کرده‌ایم استفاده کنیم.
STATE_FILE = "/data/state.json"

bot = telebot.TeleBot(TOKEN, parse_mode="MarkdownV2")

# دیکشنری سراسری برای کنترل وضعیت ربات
state = {
    "spam_active": False,
    "spam_chat_id": None,
    "tag_active": False,
    "tag_chat_id": None,
    "target_user": None
}
spam_thread = None
tag_thread = None
reply_lock_active = False

# --- توابع کمکی ---

def save_state():
    """وضعیت فعلی ربات را در فایل JSON ذخیره می‌کند."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
        print("State saved.")
    except Exception as e:
        print(f"Error saving state: {e}")

def load_state():
    """وضعیت ربات را از فایل JSON بارگذاری می‌کند."""
    global state
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state.update(json.load(f))
            print("Bot state loaded:", state)
        except Exception as e:
            print(f"Error loading state: {e}")
    else:
        print("State file not found. Starting with a fresh state.")

def is_admin(message):
    """بررسی می‌کند که آیا کاربر ارسال‌کننده دستور، ادمین گروه است یا خیر."""
    if message.chat.type == 'private':
        return True
    try:
        user_status = bot.get_chat_member(message.chat.id, message.from_user.id).status
        return user_status in ['administrator', 'creator']
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False

# --- توابع پس‌زمینه ---

def spam_sender(chat_id):
    """تا زمانی که اسپم فعال باشد، پیام‌های اسپم ارسال می‌کند."""
    global state
    print(f"Spam thread started for chat_id: {chat_id}")
    while state.get("spam_active"):
        messages = [
            "This is a spam message\\. Don't mind me\\!",
            "Spam is delicious, isn't it? 🤖",
            "Get ready for a flood of pointless messages\\!",
            "I'm just a bot doing what I do best: spamming\\."
        ]
        try:
            bot.send_message(chat_id, random.choice(messages))
        except Exception as e:
            print(f"Error sending spam message: {e}. Stopping spam.")
            state["spam_active"] = False
            save_state()
            break
        time.sleep(10)
    print(f"Spam thread stopped for chat_id: {chat_id}")


def tag_sender(chat_id):
    """تا زمانی که تگ فعال باشد، کاربر هدف را تگ می‌کند."""
    global state
    print(f"Tag thread started for @{state.get('target_user')} in chat_id: {chat_id}")
    while state.get("tag_active"):
        if not state.get("target_user"):
            print("Target user is not set. Stopping tag thread.")
            state["tag_active"] = False
            save_state()
            break
        try:
            escaped_username = state["target_user"].replace('_', '\\_').replace('*', '\\*')
            bot.send_message(chat_id, f"Hey @{escaped_username}, you've been tagged\\!")
        except Exception as e:
            print(f"Error sending tag message: {e}. Stopping tagging.")
            state["tag_active"] = False
            save_state()
            break
        time.sleep(60)
    print(f"Tag thread stopped for chat_id: {chat_id}")


# --- کنترل‌کننده‌های دستورات ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.reply_to(message, "I'm a bot designed for chaos\\. Use /help to see what I can do\\.")

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = """
*Here are my functions:*
/spam\_on \- Start 24/7 spam in this chat\.
/spam\_off \- Stop the spam\.
/target \<username\> \- Set a target for tagging\.
/tag\_on \- Start tagging the target user\.
/tag\_off \- Stop tagging the target\.
/lock\_reply \- Lock reply functionality\.
/unlock\_reply \- Unlock reply functionality\.
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['spam_on'])
def handle_spam_on(message):
    global state, spam_thread
    if not is_admin(message):
        bot.reply_to(message, "You're not an admin, so you can't use this command\\!")
        return

    if not state.get("spam_active"):
        state["spam_active"] = True
        state["spam_chat_id"] = message.chat.id
        save_state()
        spam_thread = threading.Thread(target=spam_sender, args=(message.chat.id,), daemon=True)
        spam_thread.start()
        bot.reply_to(message, "Spam mode activated\\. Prepare for the messages\\!")
    else:
        bot.reply_to(message, f"Spam is already active in chat_id: {state['spam_chat_id']}\\.")

@bot.message_handler(commands=['spam_off'])
def handle_spam_off(message):
    global state
    if not is_admin(message):
        bot.reply_to(message, "You're not an admin, so you can't use this command\\!")
        return

    if state.get("spam_active"):
        state["spam_active"] = False
        state["spam_chat_id"] = None
        save_state()
        bot.reply_to(message, "Spam mode deactivated\\. Phew, that's over\\.")
    else:
        bot.reply_to(message, "Spam is already off\\.")

@bot.message_handler(commands=['target'])
def handle_target(message):
    global state
    if not is_admin(message):
        bot.reply_to(message, "You're not an admin, so you can't use this command\\!")
        return
    try:
        target_user = message.text.split()[1].lstrip('@')
        state["target_user"] = target_user
        save_state()
        bot.reply_to(message, f"Target set to @{target_user}\\.")
    except IndexError:
        bot.reply_to(message, "Please specify a username, e\\.g\\., /target some\\_user")

@bot.message_handler(commands=['tag_on'])
def handle_tag_on(message):
    global state, tag_thread
    if not is_admin(message):
        bot.reply_to(message, "You're not an admin, so you can't use this command\\!")
        return

    if not state.get("target_user"):
        bot.reply_to(message, "No target user has been set\\. Use /target first\\.")
        return
        
    if not state.get("tag_active"):
        state["tag_active"] = True
        state["tag_chat_id"] = message.chat.id
        save_state()
        tag_thread = threading.Thread(target=tag_sender, args=(message.chat.id,), daemon=True)
        tag_thread.start()
        bot.reply_to(message, f"24/7 tagging has begun for @{state['target_user']}\\.")
    else:
        bot.reply_to(message, f"Tagging is already active for @{state['target_user']} in chat_id: {state['tag_chat_id']}\\.")

@bot.message_handler(commands=['tag_off'])
def handle_tag_off(message):
    global state
    if not is_admin(message):
        bot.reply_to(message, "You're not an admin, so you can't use this command\\!")
        return

    if state.get("tag_active"):
        state["tag_active"] = False
        state["tag_chat_id"] = None
        save_state()
        bot.reply_to(message, "Tagging has been stopped\\.")
    else:
        bot.reply_to(message, "Tagging is already off\\.")

@bot.message_handler(commands=['lock_reply'])
def handle_lock_reply(message):
    global reply_lock_active
    if not is_admin(message):
        bot.reply_to(message, "You're not an admin, so you can't use this command\\!")
        return
    reply_lock_active = True
    bot.reply_to(message, "Reply functionality is now locked\\.")

@bot.message_handler(commands=['unlock_reply'])
def handle_unlock_reply(message):
    global reply_lock_active
    if not is_admin(message):
        bot.reply_to(message, "You're not an admin, so you can't use this command\\!")
        return
    reply_lock_active = False
    bot.reply_to(message, "Reply functionality is now unlocked\\.")

@bot.message_handler(func=lambda message: reply_lock_active and message.reply_to_message)
def handle_locked_reply(message):
    try:
        if not is_admin(message):
            bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        print(f"Error deleting message: {e}")

# --- بخش اصلی اجرای ربات ---

if __name__ == "__main__":
    load_state()
    
    # از سرگیری فعالیت‌ها در صورت ری‌استارت شدن ربات
    if state.get("spam_active") and state.get("spam_chat_id"):
        chat_id = state["spam_chat_id"]
        spam_thread = threading.Thread(target=spam_sender, args=(chat_id,), daemon=True)
        spam_thread.start()

    if state.get("tag_active") and state.get("tag_chat_id") and state.get("target_user"):
        chat_id = state["tag_chat_id"]
        tag_thread = threading.Thread(target=tag_sender, args=(chat_id,), daemon=True)
        tag_thread.start()

    print("Bot is running...")
    bot.infinity_polling()