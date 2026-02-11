import logging
import sqlite3
import asyncio
import uuid
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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Database Setup
conn = sqlite3.connect('premium_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_time TIMESTAMP)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS plans (plan_id TEXT PRIMARY KEY, name TEXT, days INTEGER, price INTEGER)''')
conn.commit()

def get_setting(key, default):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else default

# --- EXPIRY CHECKER ---
async def expiry_checker():
    while True:
        now = datetime.now()
        one_hour_later = now + timedelta(hours=1)
        
        cursor.execute("SELECT user_id FROM users WHERE expiry_time <= ? AND expiry_time > ?", (one_hour_later, now))
        for user in cursor.fetchall():
            try:
                msg = ("››⚠️ Reminder: Your premium membership will expire in 1 hour.\n\n"
                       "To renew your premium membership, please Contact Our Admins.")
                await bot.send_message(user[0], msg)
            except: pass
            
        cursor.execute("SELECT user_id FROM users WHERE expiry_time <= ?", (now,))
        for user in cursor.fetchall():
            try:
                await bot.send_message(user[0], "❌ Your Membership has Expired. Please renew to continue.")
                cursor.execute("DELETE FROM users WHERE user_id=?", (user[0],))
                conn.commit()
            except: pass
        await asyncio.sleep(600)

# --- START COMMAND ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
