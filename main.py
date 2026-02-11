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
CHANNEL_LINK = 'https://t.me/+O27nU16V5VszYjg1'

# --- IMAGE IDs (WAPAS ADD KIYA) ---
IMG_FORCE_JOIN = "6ktKOox5WgWoCO_G9gHk-_IUHDyQk1t3uycUC4KOKrLEc5bV-28YG9k_z-r5UNG8"
IMG_START_MENU = "6ktKOox5WgWoCO_G9gHk-_RosAwQw-msNj_A2GBVlAIWZ4bGLo4G2gr7uGyB1W8r"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Database Setup
conn = sqlite3.connect('premium_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_time TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS files (file_id TEXT PRIMARY KEY, data TEXT, type TEXT)')
conn.commit()

# --- AUTO DELETE HELPER ---
async def delete_after_delay(chat_id, message_id, delay, alert=None):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
        if alert: await bot.send_message(chat_id, alert)
    except: pass

# --- START COMMAND ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    # Join Buttons & Captions
    kb_join = InlineKeyboardMarkup().add(InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    kb_join.add(InlineKeyboardButton("🔄 Verify Membership", callback_data="check_join"))

    if args and args.startswith('file_'):
        cursor.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
        if not cursor.fetchone():
            return await bot.send_photo(user_id, IMG_FORCE_JOIN, 
                                      caption="❌ **Premium Content!**\n\nPehle channel join karein aur membership lein.", 
                                      reply_markup=kb_join)
        
        f_key = args.replace('file_', '')
        cursor.execute("SELECT data FROM files WHERE file_id=?", (f_key,))
        file_data = cursor.fetchone()
        if file_data:
            msg = await message.answer(f"✅ **Premium Content:** {file_data[0]}\n\n⚠️ Yeh link 10 minute mein delete ho jayega.")
            asyncio.create_task(delete_after_delay(user_id, msg.message_id, 600, "🗑️ Link delete kar diya gaya hai."))
        return

    # Start Menu with Photo & Caption
    try:
        await bot.send_photo(user_id, IMG_START_MENU, 
                             caption=f"👋 Hello {message.from_user.first_name}!\n\nWelcome to our Premium Bot. Join our channel to unlock all features.", 
                             reply_markup=kb_join)
    except:
        await message.answer(f"Hello {message.from_user.first_name}! Join channel to continue.", reply_markup=kb_join)

# --- CALLBACKS ---
@dp.callback_query_handler(lambda c: c.data == "check_join")
async def verify(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 BUY PREMIUM 💎", callback_data="buy_premium"))
    await callback.message.answer("✅ **Verification Success!**\n\nAb aap premium plans dekh sakte hain.", reply_markup=kb)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "buy_premium")
async def buy_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💳 Pay ₹20 (1 Day)", callback_data="pay_20_1"))
    await callback.message.answer("💎 **Premium Plan:**\n\n• 1 Day Access: ₹20\n\nInstant access ke liye UPI karein.", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('pay_'))
async def qr_handler(callback: types.CallbackQuery):
    _, price, days = callback.data.split('_')
    upi_url = f"upi://pay?pa={UPI_ID}&am={price}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_url}"
    
    qr_msg = await bot.send_photo(callback.from_user.id, qr_url, 
                                 caption=f"💰 **Amount: ₹{price}**\n\n⚠️ QR Code 15 min mein delete hoga. Payment ke baad screenshot bhein.")
    asyncio.create_task(delete_after_delay(callback.from_user.id, qr_msg.message_id, 900, "⌛ QR Expired!"))

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
