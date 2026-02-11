import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
API_TOKEN = '8245244001:AAEDmWAXRk7U-YG36gXeDJL2eEbbJs2dJNA'
ADMINS = [8149275394, 1936430807]
UPI_ID = 'BHARATPE09910027091@yesbankltd'

# --- IMAGE IDs ---
IMG_FORCE_JOIN = "6ktKOox5WgWoCO_G9gHk-_IUHDyQk1t3uycUC4KOKrLEc5bV-28YG9k_z-r5UNG8"
IMG_START_MENU = "6ktKOox5WgWoCO_G9gHk-_RosAwQw-msNj_A2GBVlAIWZ4bGLo4G2gr7uGyB1W8r"
IMG_PREMIUM_INFO = "6ktKOox5WgWoCO_G9gHk-0I8ckMM7pE26WyuOUC43SLCnUZakTDd2EMs2mnKaguH"
IMG_PLANS_LIST = "6ktKOox5WgWoCO_G9gHk-yF1l56JzaL6ivArWP4pgATkmr0Ke1l-wuPmHNRzRoP1"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Database Setup
conn = sqlite3.connect('premium_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_time TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS all_users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS files (file_id TEXT PRIMARY KEY, data TEXT, type TEXT)')
conn.commit()

def get_setting(key, default):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else default

# --- AUTO DELETE HELPER ---
async def delete_after_delay(chat_id, message_id, delay, alert_text=None):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
        if alert_text:
            await bot.send_message(chat_id, alert_text)
    except: pass

# --- EXPIRY CHECKER ---
async def expiry_checker():
    while True:
        now = datetime.now()
        cursor.execute("SELECT user_id, expiry_time FROM users")
        for user_id, expiry_str in cursor.fetchall():
            try:
                expiry_dt = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
                if now >= expiry_dt:
                    try: await bot.send_message(user_id, "❌ Your Membership has Expired. Please renew to continue.")
                    except: pass
                    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
                    conn.commit()
            except: pass
        await asyncio.sleep(60)

# --- START COMMAND ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO all_users VALUES (?)", (user_id,))
    conn.commit()
    
    args = message.get_args()
    if args and args.startswith('file_'):
        cursor.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
        if not cursor.fetchone():
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 BUY PREMIUM 💎", callback_
