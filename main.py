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

# --- IMAGE IDs (Corrected) ---
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
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 BUY PREMIUM 💎", callback_data="buy_premium"))
            return await bot.send_photo(user_id, IMG_START_MENU, caption="❌ This is a Premium File. Buy membership to access!", reply_markup=kb)
        
        f_key = args.replace('file_', '')
        cursor.execute("SELECT data, type FROM files WHERE file_id=?", (f_key,))
        file_data = cursor.fetchone()
        if file_data:
            alert = "⚠️ Yeh content 10 minute mein delete ho jayega."
            if file_data[1] == 'url':
                msg = await message.answer(f"🔗 **Your Link:** {file_data[0]}\n\n{alert}")
            else:
                msg = await bot.send_photo(user_id, file_data[0], caption=f"✅ **Premium Content**\n\n{alert}")
            asyncio.create_task(delete_after_delay(user_id, msg.message_id, 600, "🗑️ Link/File deleted after 10 mins."))
        return

    f_join = get_setting('f_join', 'None')
    if f_join != 'None' and f_join != "":
        try:
            member = await bot.get_chat_member(f_join, user_id)
            if member.status in ['left', 'kicked']:
                kb = InlineKeyboardMarkup().add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{f_join.replace('@','')}"))
                kb.add(InlineKeyboardButton("🔄 Verify Membership", callback_data="check_join"))
                return await bot.send_photo(user_id, IMG_FORCE_JOIN, caption=f"Hello {message.from_user.first_name}\n\nYou need to join in my Channel/Group to use me", reply_markup=kb)
        except: pass

    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 BUY PREMIUM 💎", callback_data="buy_premium"))
    await bot.send_photo(user_id, IMG_START_MENU, caption=f"Hello {message.from_user.first_name}, Welcome!", reply_markup=kb)

# --- MENUS ---
@dp.callback_query_handler(lambda c: c.data in ["buy_premium", "check_join", "pay_upi_list"])
async def menu_handler(callback: types.CallbackQuery):
    if callback.data in ["buy_premium", "check_join"]:
        caption = f"👋 Hello {callback.from_user.first_name}\n\n🎖️ Want Premium?\n\n• 💳 Pay with UPI (Instant)"
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💳 Pay with UPI", callback_data="pay_upi_list"))
        await bot.send_photo(callback.from_user.id, IMG_PREMIUM_INFO, caption=caption, reply_markup=kb)
    elif callback.data == "pay_upi_list":
        caption = "✦ 𝗦𝗛𝗢𝗥𝗧𝗡𝗘𝗥 𝗣𝗟𝗔𝗡𝗦\n›› 1 days : ₹20\n›› 7 Days : ₹50\n›› 15 days : ₹120\n›› 1 Months : ₹200\n\n❐ Sᴇɴᴅ ᴀ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ ᴀғᴛᴇʀ ᴘᴀʏᴍᴇɴᴛ ✓"
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("1 DAY", callback_data="pay_20_1"),
            InlineKeyboardButton("7 DAY", callback_data="pay_50_7"),
            InlineKeyboardButton("15 DAY", callback_data
