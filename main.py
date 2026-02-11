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
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 BUY PREMIUM 💎", callback_data="buy_premium"))
            return await bot.send_photo(user_id, IMG_START_MENU, caption="❌ This is a Premium File. Buy membership to access!", reply_markup=kb)
        
        f_key = args.replace('file_', '')
        cursor.execute("SELECT data, type FROM files WHERE file_id=?", (f_key,))
        file_data = cursor.fetchone()
        if file_data:
            alert = "⚠️ Yeh content 10 minute mein delete ho jayega."
            if file_data[1] == 'url':
                msg = await message.answer(f"🔗 Your Link: {file_data[0]}\n\n{alert}")
            else:
                msg = await bot.send_photo(user_id, file_data[0], caption=f"✅ Premium Content\n\n{alert}")
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
        caption = "✦ SHORTNER PLANS\n›› 1 days : ₹20\n›› 7 Days : ₹50\n›› 15 days : ₹120\n›› 1 Months : ₹200\n\n**AFTER PAYMENT:**\nSEND A SCREENSHOT & WAIT ✓"
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("1 DAY", callback_data="pay_20_1"),
            InlineKeyboardButton("7 DAY", callback_data="pay_50_7"),
            InlineKeyboardButton("15 DAY", callback_data="pay_120_15"),
            InlineKeyboardButton("1 MONTH", callback_data="pay_200_30")
        )
        await bot.send_photo(callback.from_user.id, IMG_PLANS_LIST, caption=caption, reply_markup=kb)
    await callback.message.delete()

@dp.callback_query_handler(lambda c: c.data.startswith('pay_'))
async def qr_handler(callback: types.CallbackQuery):
    _, price, days = callback.data.split('_')
    upi_url = f"upi://pay?pa={UPI_ID}&am={price}&tn=Premium_{days}Days"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_url}"
    qr_msg = await bot.send_photo(callback.from_user.id, qr_url, caption=f"💰 Amount: ₹{price}\n\n⚠️ QR expires in 15 mins. Send screenshot after pay.")
    asyncio.create_task(delete_after_delay(callback.from_user.id, qr_msg.message_id, 900, "⌛ QR Expired and Deleted."))

# --- ADMIN ---
@dp.message_handler(content_types=['photo', 'text'])
async def admin_handler(message: types.Message):
    if message.from_user.id not in ADMINS:
        if message.photo:
            await message.answer("✅ membership Request Submitted! Being verified.")
            for adm in ADMINS:
                kb = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("Approve 1 Day", callback_data=f"app_1_{message.from_user.id}"),
                    InlineKeyboardButton("Approve 7 Day", callback_data=f"app_7_{message.from_user.id}")
                )
                await bot.send_photo(adm, message.photo[-1].file_id, caption=f"New Proof from {message.from_user.id}", reply_markup=kb)
        return

    if message.text and (message.text.startswith('http') or 't.me' in message.text):
        f_id = str(datetime.now().timestamp()).replace('.','')
        cursor.execute("INSERT INTO files VALUES (?, ?, ?)", (f_id, message.text, 'url'))
        conn.commit()
        await message.answer(f"✅ Link Saved!\nShare Link: https://t.me/{(await bot.get_me()).username}?start=file_{f_id}")
    elif message.photo:
        f_id = message.photo[-1].file_id
        cursor.execute("INSERT OR IGNORE INTO files VALUES (?, ?, ?)", (f_id, f_id, 'photo'))
        conn.commit()
        await message.answer(f"✅ Photo Saved!\nShare Link: https://t.me/{(await bot.get_me()).username}?start=file_{f_id}")

@dp.callback_query_handler(lambda c: c.data.startswith('app_'))
async def approval_handler(callback: types.CallbackQuery):
    _, days, uid = callback.data.split('_')
    expiry_str = (datetime.now() + timedelta(days=int(days))).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, expiry_str))
    conn.commit()
    await bot.send_message(uid, "✅ Payment Successful! Premium Activated!")
    await callback.answer("Approved!")

if __name__ == '__main__':
    keep_alive()
    loop = asyncio.get_event_loop()
    loop.create_task(expiry_checker())
    executor.start_polling(dp, skip_updates=True)
