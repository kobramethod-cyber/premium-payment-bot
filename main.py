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

# Database Setup
conn = sqlite3.connect('premium_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_time TIMESTAMP)''')
# Naya table plans store karne ke liye
cursor.execute('''CREATE TABLE IF NOT EXISTS plans (plan_id TEXT PRIMARY KEY, name TEXT, days INTEGER, price INTEGER)''')

# Default Plans Insert (Sirf pehli baar ke liye)
cursor.execute("INSERT OR IGNORE INTO plans VALUES ('1d', '1 Day Access', 1, 20)")
cursor.execute("INSERT OR IGNORE INTO plans VALUES ('7d', '7 Days Access', 7, 100)")
cursor.execute("INSERT OR IGNORE INTO plans VALUES ('15d', '15 Days Access', 15, 180)")
cursor.execute("INSERT OR IGNORE INTO plans VALUES ('1m', '1 Month Access', 30, 300)")
conn.commit()

def get_setting(key, default):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else default

# --- START COMMAND ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    f_join = get_setting('f_join', 'None')
    
    if f_join != 'None':
        try:
            member = await bot.get_chat_member(f_join, user_id)
            if member.status == 'left':
                kb = InlineKeyboardMarkup().add(InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{f_join.replace('@','')}"))
                kb.add(InlineKeyboardButton("🔄 Click here after Joining", callback_data="check_join"))
                return await message.answer(f"⚠️ **Access Denied!**\n\nPlease join our channel {f_join} to use this bot.", reply_markup=kb, parse_mode="Markdown")
        except: pass

    cursor.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
    is_premium = cursor.fetchone()

    if is_premium:
        target = get_setting('target_link', 'Not Set')
        await message.answer(f"🌟 **Welcome Back, Premium Member!**\n\n🔗 Your Private Access Link:\n{target}", parse_mode="Markdown")
    else:
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 Buy Premium Subscription", callback_data="show_plans"))
        await message.answer("👋 **Welcome to Premium Bot**\n\nUnlock exclusive content by purchasing a subscription.", reply_markup=kb, parse_mode="Markdown")

# --- CALLBACK: SHOW PLANS (Dynamic) ---
@dp.callback_query_handler(lambda c: c.data == "show_plans" or c.data == "check_join")
async def show_plans(callback: types.CallbackQuery):
    cursor.execute("SELECT plan_id, name, price FROM plans")
    all_plans = cursor.fetchall()
    
    kb = InlineKeyboardMarkup(row_width=2)
    for p_id, p_name, p_price in all_plans:
        kb.insert(InlineKeyboardButton(f"{p_name} - ₹{p_price}", callback_data=f"buy_{p_id}"))
    
    await callback.message.edit_text("⚡ **Select Your Premium Plan:**", reply_markup=kb, parse_mode="Markdown")

# --- CALLBACK: GENERATE QR ---
@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def generate_qr(callback: types.CallbackQuery):
    p_id = callback.data.split('_')[1]
    cursor.execute("SELECT name, price FROM plans WHERE plan_id=?", (p_id,))
    plan = cursor.fetchone()
    
    if plan:
        name, price = plan
        upi_url = f"upi://pay?pa={UPI_ID}&am={price}&tn=Premium_{p_id}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_url}"
        
        caption = (f"💳 **Payment Details**\n\n🔹 Plan: `{name}`\n🔹 Amount: `₹{price}`\n\n"
                   f"━━━━━━━━━━━━━━\n✅ **Pay using any UPI App**\n📸 **Send Screenshot** after payment.")
        await bot.send_photo(callback.from_user.id, qr_url, caption=caption, parse_mode="Markdown")
    await callback.answer()

# --- PHOTO HANDLER & ADMIN APPROVAL ---
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    await message.answer("🚀 **Proof Sent!** Verification in progress...")
    cursor.execute("SELECT plan_id, name FROM plans")
    all_plans = cursor.fetchall()
    
    for admin in ADMINS:
        kb = InlineKeyboardMarkup(row_width=2)
        for p_id, p_name in all_plans:
            kb.insert(InlineKeyboardButton(f"Approve {p_id} ✅", callback_data=f"app_{p_id}_{message.from_user.id}"))
        kb.add(InlineKeyboardButton("Reject ❌", callback_data=f"rej_0_{message.from_user.id}"))
        
        await bot.send_photo(admin, message.photo[-1].file_id, caption=f"New Payment from `{message.from_user.id}`", reply_markup=kb, parse_mode="Markdown")

# --- ADMIN ACTION ---
@dp.callback_query_handler(lambda c: c.data.startswith(('app_', 'rej_')))
async def admin_act(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS: return
    act, p_id, uid = callback.data.split('_')
    
    if act == 'app':
        cursor.execute("SELECT days FROM plans WHERE plan_id=?", (p_id,))
        res = cursor.fetchone()
        days = res[0] if res else 1
        expiry = datetime.now() + timedelta(days=days)
        cursor.execute("INSERT OR REPLACE INTO users (user_id, expiry_time) VALUES (?, ?)", (uid, expiry))
        conn.commit()
        await bot.send_message(uid, f"🎊 **Premium Activated!**\nValid for `{days}` days.")
        await callback.answer("Activated!")
    else:
        await bot.send_message(uid, "❌ **Payment Rejected.**")
        await callback.answer("Rejected!")

# --- DYNAMIC ADMIN COMMANDS ---
@dp.message_handler(commands=['addplan'])
async def add_plan(message: types.Message):
    if message.from_user.id not in ADMINS: return
    try:
        args = message.get_args().split() # Format: id name_with_underscore days price
        p_id, p_name, p_days, p_price = args
        p_name = p_name.replace('_', ' ')
        cursor.execute("INSERT OR REPLACE INTO plans VALUES (?, ?, ?, ?)", (p_id, p_name, int(p_days), int(p_price)))
        conn.commit()
        await message.answer(f"✅ Plan `{p_name}` Added/Updated!")
    except:
        await message.answer("❌ Format: `/addplan 7d 7_Days_Special 7 100`")

@dp.message_handler(commands=['setlink', 'setchannel'])
async def set_settings(message: types.Message):
    if message.from_user.id not in ADMINS: return
    cmd, val = message.get_command(), message.get_args()
    if 'link' in cmd: cursor.execute("INSERT OR REPLACE INTO settings VALUES ('target_link', ?)", (val,))
    else: cursor.execute("INSERT OR REPLACE INTO settings VALUES ('f_join', ?)", (val,))
    conn.commit()
    await message.answer(f"✅ `{cmd}` updated!")

if __name__ == '__main__':
    keep_alive()
    executor.start_polling(dp, skip_updates=True)
