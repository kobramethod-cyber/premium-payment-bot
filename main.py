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

# Photo IDs (Inhe bot ko photo bhej kar mili ID se replace karein)
WELCOME_PHOTO = "https://telegra.ph/file/de2063065183887709335.jpg"
PLAN_MENU_PHOTO = "https://telegra.ph/file/de2063065183887709335.jpg" 

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

# --- EXPIRY CHECKER (Exact Reminder) ---
async def expiry_checker():
    while True:
        now = datetime.now()
        one_hour_later = now + timedelta(hours=1)
        
        # 1 Hour Reminder
        cursor.execute("SELECT user_id FROM users WHERE expiry_time <= ? AND expiry_time > ?", (one_hour_later, now))
        for user in cursor.fetchall():
            try:
                await bot.send_message(user[0], "››⚠️ Reminder: Your premium membership will expire in 1 hour.\n\nTo renew your premium membership, please Contact Our Admins.")
            except: pass
            
        # Actual Expiry
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
    user_id = message.from_user.id
    f_join = get_setting('f_join', 'None')
    
    if f_join != 'None':
        try:
            member = await bot.get_chat_member(f_join, user_id)
            if member.status in ['left', 'kicked']:
                kb = InlineKeyboardMarkup().add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{f_join.replace('@','')}"))
                kb.add(InlineKeyboardButton("🔄 Verify Membership", callback_data="check_join"))
                return await bot.send_photo(user_id, WELCOME_PHOTO, caption=f"⚠️ **Access Denied!**\n\nPlease join our channel {f_join} to use this bot.", reply_markup=kb)
        except: pass

    welcome_text = f"Hello {message.from_user.full_name}\n\nI can store private files in Specified Channel and other users can access it from special link."
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("⭐ PREMIUM", callback_data="show_plans"),
        InlineKeyboardButton("👨‍💻 ADMIN", callback_data="admin_info"),
        InlineKeyboardButton("⌛ Help Menu", callback_data="help"),
        InlineKeyboardButton("🔒 CLOSE", callback_data="close"),
        InlineKeyboardButton("🤖 DEVELOPER", url="https://t.me/your_handle")
    )
    await bot.send_photo(user_id, WELCOME_PHOTO, caption=welcome_text, reply_markup=kb)

# --- PREMIUM MENU & PLANS ---
@dp.callback_query_handler(lambda c: c.data in ["show_plans", "check_join", "start_again"])
async def show_plans(callback: types.CallbackQuery):
    cursor.execute("SELECT plan_id, name, price FROM plans")
    all_plans = cursor.fetchall()
    
    plan_text = "✦ **SHORTNER PLANS**\n\n**DURATION & PRICE**\n"
    kb = InlineKeyboardMarkup(row_width=2)
    for p_id, name, price in all_plans:
        plan_text += f"›› {name} : ₹{price}\n"
        kb.insert(InlineKeyboardButton(name.upper(), callback_data=f"pay_{p_id}"))
    
    plan_text += "\n❒ **PAYMENT METHODS**\n❒ paytm • gpay • phone pay • upi and qr"
    plan_text += "\n\n✦ PREMIUM WILL BE ADDED AUTOMATICALLY ONCE PAID"
    plan_text += "\n\n✦ **AFTER PAYMENT:**\n❒ SEND A SCREENSHOT & WAIT A FE
