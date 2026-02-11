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
IMG_START_MENU = "6ktKOox5WgWoCO_G9gHk-_RosAwQw-msNj_A2GBVlAIWZ4bGLo4G2gr7uGyB1W8r"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- AUTO DELETE FUNCTIONS ---

async def delete_after_delay(chat_id, message_id, delay, alert_text=None):
    """Nirdharit samay ke baad message delete karne ke liye"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
        if alert_text:
            await bot.send_message(chat_id, alert_text)
    except Exception as e:
        logging.error(f"Error deleting message: {e}")

# --- START COMMAND (Handling Shared Links with Auto-Delete) ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    if args and args.startswith('file_'):
        # Check Membership
        conn = sqlite3.connect('premium_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
        is_premium = cursor.fetchone()
        
        if not is_premium:
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 BUY PREMIUM 💎", callback_data="buy_premium"))
            return await bot.send_photo(user_id, IMG_START_MENU, caption="❌ Access Denied! Buy membership to see this.", reply_markup=kb)
        
        # Premium Content Delivery
        f_key = args.replace('file_', '')
        cursor.execute("SELECT data, type FROM files WHERE file_id=?", (f_key,))
        file_data = cursor.fetchone()
        conn.close()

        if file_data:
            sent_msg = None
            alert_msg = "⚠️ Suraksha kaaranon se, yeh link/file 10 minute mein delete kar di jayegi."
            
            if file_data[1] == 'url':
                sent_msg = await message.answer(f"🔗 **Your Premium Link:**\n{file_data[0]}\n\n{alert_msg}")
            else:
                sent_msg = await bot.send_photo(user_id, file_data[0], caption=f"✅ **Premium Content**\n\n{alert_msg}")
            
            # 10 Minute (600 seconds) baad delete
            if sent_msg:
                asyncio.create_task(delete_after_delay(user_id, sent_msg.message_id, 600, "🗑️ Premium link/file 10 minute poore hone par delete kar di gayi hai."))
        return

    # Normal Start
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 BUY PREMIUM 💎", callback_data="buy_premium"))
    await bot.send_photo(user_id, IMG_START_MENU, caption=f"Hello {message.from_user.first_name}, Welcome!", reply_markup=kb)

# --- QR GENERATOR (With 15 Min Auto-Delete) ---
@dp.callback_query_handler(lambda c: c.data.startswith('pay_'))
async def generate_qr(callback: types.CallbackQuery):
    _, price, days = callback.data.split('_')
    upi_url = f"upi://pay?pa={UPI_ID}&am={price}&tn=Premium_{days}Days"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_url}"
    
    caption = f"💰 **Amount:** ₹{price}\n✅ Scan QR to pay\n\n⚠️ Yeh QR code 15 minute mein expire ho jayega."
    qr_msg = await bot.send_photo(callback.from_user.id, qr_url, caption=caption)
    
    # 15 Minute (900 seconds) baad delete
    asyncio.create_task(delete_after_delay(callback.from_user.id, qr_msg.message_id, 900, "⌛ Samay samapt! QR code expire hone ke kaaran delete kar diya gaya hai."))

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
