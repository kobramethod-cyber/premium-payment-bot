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

# Screenshots wali Images
WELCOME_PHOTO = "https://telegra.ph/file/de2063065183887709335.jpg"
PLAN_PHOTO = "https://telegra.ph/file/de2063065183887709335.jpg" 

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
                await bot.send_message(user[0], "››⚠️ Reminder: Your premium membership will expire in 1 hour.\n\nTo renew your premium membership, please Contact Our Admins.")
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

# --- PLANS MENU (Fixed Syntax) ---
@dp.callback_query_handler(lambda c: c.data in ["show_plans", "check_join"])
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
    plan_text += "\n\n✦ **AFTER PAYMENT:**\n❒ SEND A SCREENSHOT & WAIT A FEW MINUTES FOR ACTIVATION ✓"
    
    kb.add(InlineKeyboardButton("✨ Custom Plan ✨", callback_data="custom"), InlineKeyboardButton("‹ Back", callback_data="start_again"))
    await bot.send_photo(callback.from_user.id, PLAN_PHOTO, caption=plan_text, reply_markup=kb, parse_mode="Markdown")
    await callback.message.delete()

# --- PAYMENT QR ---
@dp.callback_query_handler(lambda c: c.data.startswith('pay_'))
async def generate_qr(callback: types.CallbackQuery):
    p_id = callback.data.split('_')[1]
    cursor.execute("SELECT name, price FROM plans WHERE plan_id=?", (p_id,))
    name, price = cursor.fetchone()
    trx_id = f"TRX{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
    upi_url = f"upi://pay?pa={UPI_ID}&am={price}&tn=Premium_{p_id}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_url}"
    
    caption = (f"✦ **PREMIUM PAYMENT**\n\n❒ **Amount:** ₹{price}\n≡ **Validity:** {name}\n"
               f"❒ **Transaction ID:** `{trx_id}`\n\n≡ **SCAN THIS QR WITH ANY UPI APP TO PAY.**\n\n"
               f"✦ **OR tap here to pay directly**\n›› [Pay ₹{price} via UPI]({upi_url})\n\n"
               f"✦ PREMIUM WILL BE ADDED AUTOMATICALLY IF PAID WITHIN 5 MINUTES...")
    
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("📲 Send Screenshot", callback_data="upload_proof"))
    kb.add(InlineKeyboardButton("❌ CANCEL", callback_data="show_plans"))
    await bot.send_photo(callback.from_user.id, qr_url, caption=caption, reply_markup=kb, parse_mode="Markdown")

# --- PHOTO HANDLER ---
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    photo_id = message.photo[-1].file_id
    if message.from_user.id in ADMINS:
        return await message.answer(f"🖼 **Admin, Photo ID:**\n\n`{photo_id}`")

    await message.answer("✅ premium membership Request Submitted!\n\n⚡ Your proof is being verified.\n📝 Status: Pending\n⏳ Time: 3 Hours (Max)\n\n🟢 You will be notified automatically once funds are added.")
    
    cursor.execute("SELECT plan_id, name FROM plans")
    all_plans = cursor.fetchall()
    for admin in ADMINS:
        kb = InlineKeyboardMarkup(row_width=2)
        for p_id, p_name in all_plans:
            kb.insert(InlineKeyboardButton(f"Approve {p_name} ✅", callback_data=f"app_{p_id}_{message.from_user.id}"))
        kb.add(InlineKeyboardButton("Reject ❌", callback_data=f"rej_0_{message.from_user.id}"))
        await bot.send_photo(admin, photo_id, caption=f"New Payment from {message.from_user.id}", reply_markup=kb)

# --- ADMIN CMDS ---
@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMINS: return
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("➕ Add Plan", callback_data="adm_add"),
        InlineKeyboardButton("🗑 Delete Plan", callback_data="adm_del"),
        InlineKeyboardButton("🔗 Set Link", callback_data="adm_link"),
        InlineKeyboardButton("📢 Set F-Join", callback_data="adm_fjoin")
    )
    await message.answer("⚙️ **Admin Control Panel**", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith(('app_', 'rej_')))
async def admin_approval(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS: return
    act, p_id, uid = callback.data.split('_')
    if act == 'app':
        cursor.execute("SELECT days, name FROM plans WHERE plan_id=?", (p_id,))
        days, plan_name = cursor.fetchone()
        expiry = datetime.now() + timedelta(days=days)
        cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, expiry))
        conn.commit()
        await bot.send_message(uid, f"✅ Pᴀʏᴍᴇɴᴛ Sᴜᴄᴄᴇssғᴜʟ!\n\n🎉 Pʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ғᴏ
