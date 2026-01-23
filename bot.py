import os
import telebot
import requests
import threading
from flask import Flask
import time
import random
import string

# --- CONFIGURATION ---
# 1. Get from Environment Variables (Render)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8506486755:AAGfitu7I_l31I0orQZvw4i4-8NcvdY-UeA')
API_URL = 'https://srfigservices.online/api.php'
API_PASSWORD = os.environ.get('API_PASSWORD', '908878')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- HELPER ---
def api_call(action, params=None):
    if params is None:
        params = {}
    
    try:
        params['password'] = API_PASSWORD
        params['action'] = action
        response = requests.get(API_URL, params=params)
        return response.json()
    except Exception as e:
        print(f'API Error: {e}')
        return {'status': 'error', 'message': 'Connection failed'}

# --- COMMANDS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    name = message.from_user.first_name
    msg = (
        f"<b>Welcome {name}!</b>\n\n"
        "Commands:\n"
        "/create [username] - Create single inbox\n"
        "/bulk [qty] - Create random inboxes (Max 50)\n"
        "/stats - View your usage"
    )
    bot.reply_to(message, msg, parse_mode='HTML')

@bot.message_handler(commands=['stats'])
def send_stats(message):
    res = api_call('get_stats', {'chat_id': message.chat.id})
    if res.get('status') == 'success':
        bot.reply_to(message, f"📊 <b>Your Stats</b>\n\nTotal Emails Created: <b>{res.get('count')}</b>", parse_mode='HTML')
    else:
        bot.reply_to(message, 'Error fetching stats')

@bot.message_handler(commands=['create'])
def create_user(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, 'Usage: /create username')
        return

    username = parts[1]
    
    # Simple validation using isalnum logic (but allowing dots is tricky in pure python isalnum, so we just pass to API usually)
    # The PHP API does strict regex check anyway.
    
    res = api_call('add_user', {'user': username})
    
    if res.get('status') == 'success':
        # Log stats
        full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
        api_call('update_stats', {'chat_id': message.chat.id, 'name': full_name, 'count': 1})
        
        bot.reply_to(message, f"✅ Created: <b>{res.get('email')}</b>", parse_mode='HTML')
    else:
        bot.reply_to(message, f"❌ Error: {res.get('message')}")

@bot.message_handler(commands=['bulk'])
def bulk_create(message):
    parts = message.text.split()
    qty = 10
    if len(parts) > 1:
        try:
            qty = int(parts[1])
        except ValueError:
            pass
            
    if qty > 50: qty = 50
    if qty < 1: qty = 1

    res = api_call('bulk_gen', {'qty': qty})

    if res.get('status') == 'success':
        full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
        api_call('update_stats', {'chat_id': message.chat.id, 'name': full_name, 'count': qty})

        email_list = "\n".join(res.get('emails', []))
        bot.reply_to(message, f"✅ Generated {qty} emails:\n\n<code>{email_list}</code>", parse_mode='HTML')
    else:
        bot.reply_to(message, f"❌ Error: {res.get('message', 'Unknown')}")

# --- WEB SERVER (Render Support) ---
@app.route('/')
def index():
    return """
    <html>
        <head><title>Telegram Bot Status</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1 style="color: #3498db;">✅ Python Bot is Running!</h1>
            <p>Processing Telegram updates...</p>
            <p>Status: <strong>Online</strong></p>
        </body>
    </html>
    """

def run_web():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Start Web Server in Thread
    t = threading.Thread(target=run_web)
    t.start()
    
    # Start Bot (Polling)
    print("Python Bot Started...")
    bot.infinity_polling()
