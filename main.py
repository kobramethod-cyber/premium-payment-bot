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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Database
conn = sqlite3.connect('premium_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_time TIMESTAMP)''')
conn.commit()

def get_setting(key, default):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else default

def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

# --- START COMMAND (Step 1: Force Join) ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    f_join = get_setting('f_join', 'None')
    
    # Check Force Join
    if f_join != 'None':
        try:
            member = await bot.get_chat_member(f_join, user_id)
            if member.status == 'left':
                kb = InlineKeyboardMarkup().add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{f_join.replace('@','')}"))
                kb.add(InlineKeyboardButton("🔄 Click here after Joining", callback_data="check_join"))
                return await message.answer(f"⚠️ **Access Denied!**\n\nPlease join our channel {f_join} to use this bot.", reply_markup=kb, parse_mode="Markdown")
        except: pass

    # Step 2: Main Menu
    cursor.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
    is_premium = cursor.fetchone()

    if is_premium:
        target = get_setting('target_link', 'Not Set')
        await message.answer(f"🌟 **Welcome Back, Premium Member!**\n\n🔗 Your Private Access Link:\n{target}", parse_mode="Markdown")
    else:
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 Buy Premium Subscription", callback_data="show_plans"))
        await message.answer("👋 **Welcome to Premium Bot**\n\nUnlock exclusive content by purchasing a subscription.", reply_markup=kb, parse_mode="Markdown")

# --- CALLBACK HANDLERS ---
@dp.callback_query_handler(lambda c: c.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery):
    await callback.answer("Checking...")
    await start_cmd(callback.message)

@dp.callback_query_handler(lambda c: c.data == "show_plans")
async def show_plans(callback: types.CallbackQuery):
    p1, p2 = get_setting('p_day', '20'), get_setting('p_month', '200')
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(f"⏳ 1 Day Access - ₹{p1}", callback_data="buy_1d"),
        InlineKeyboardButton(f"📅 1 Month Access - ₹{p2}", callback_data="buy_1m"),
        InlineKeyboardButton("⬅️ Back", callback_data="check_join")
    )
    await callback.message.edit_text("⚡ **Select Your Premium Plan:**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def generate_qr(callback: types.CallbackQuery):
    plan = "1 Day" if "1d" in callback.data else "1 Month"
    amt = get_setting('p_day' if "1d" in callback_query.data else 'p_month', '20') if "1d" in callback.data else get_setting('p_month', '200')
    
    upi_url = f"upi://pay?pa={UPI_ID}&am={amt}&tn=Premium_Access"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_url}"
    
    caption = (f"💳 **Payment Details**\n\n"
               f"🔹 Plan: `{plan}`\n"
               f"🔹 Amount: `₹{amt}`\n\n"
               f"━━━━━━━━━━━━━━\n"
               f"✅ **Pay using any UPI App** (Paytm/GPay/PhonePe)\n"
               f"📸 **Send Screenshot** after successful payment.")
    
    await bot.send_photo(callback.from_user.id, qr_url, caption=caption, parse_mode="Markdown")
    await callback.answer()

# --- PHOTO HANDLER & ADMIN ACTIONS ---
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    await message.answer("🚀 **Proof Sent!**\nAdmin will verify your payment within 1-3 hours.")
    for admin in ADMINS:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Approve 1 Day ✅", callback_data=f"app_1d_{message.from_user.id}"),
            InlineKeyboardButton("Approve 1 Month ✅", callback_data=f"app_1m_{message.from_user.id}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"rej_{message.from_user.id}")
        )
        await bot.send_photo(admin, message.photo[-1].file_id, caption=f"New Payment from `{message.from_user.id}`", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith(('app_', 'rej_')))
async def admin_act(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS: return
    act, plan, uid = callback.data.split('_')
    if act == 'app':
        days = 1 if plan == '1d' else 30
        expiry = datetime.now() + timedelta(days=days)
        cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, expiry))
        conn.commit()
        await bot.send_message(uid, f"🎊 **Premium Activated!**\n\nEnjoy your `{days}` days of access.")
        await callback.answer("Activated!")
    else:
        await bot.send_message(uid, "❌ **Payment Rejected.** Proof invalid.")
        await callback.answer("Rejected!")

# --- ADMIN PANEL ---
@dp.message_handler(commands=['admin'])
async def admin_p(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("⚙️ **Admin Control Panel**\n\n/setprice_day [Rs]\n/setprice_month [Rs]\n/setlink [URL]\n/setchannel [@Username]")

@dp.message_handler(commands=['setprice_day', 'setprice_month', 'setlink', 'setchannel'])
async def updates(message: types.Message):
    if message.from_user.id not in ADMINS: return
    cmd, val = message.get_command(), message.get_args()
    if not val: return await message.answer("Error: Value missing.")
    if 'day' in cmd: set_setting('p_day', val)
    elif 'month' in cmd: set_setting('p_month', val)
    elif 'link' in cmd: set_setting('target_link', val)
    elif 'channel' in cmd: set_setting('f_join', val)
    await message.answer(f"✅ Successfully updated: `{cmd}`", parse_mode="Markdown")

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
