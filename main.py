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

# IMAGE IDs
IMG_FORCE_JOIN = "6ktKOox5WgWoCO_G9gHk-_IUHDyQk1t3uycUC4KOKrLEc5bV-28YG9k_z-r5UNG8"
IMG_START_MENU = "6ktKOox5WgWoCO_G9gHk-_RosAwQw-msNj_A2GBVlAIWZ4bGLo4G2gr7uGyB1W8r"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Database Setup
conn = sqlite3.connect('premium_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_time TEXT, reminded INTEGER DEFAULT 0)')
cursor.execute('CREATE TABLE IF NOT EXISTS all_users (user_id INTEGER PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS files (file_id TEXT PRIMARY KEY, data TEXT)')
conn.commit()

async def delete_after_delay(chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try: await bot.delete_message(chat_id, message_id)
    except: pass

# --- EXPIRY CHECKER WITH 1-HOUR REMINDER ---
async def expiry_checker():
    while True:
        now = datetime.now()
        one_hour_later = now + timedelta(hours=1)
        cursor.execute("SELECT user_id, expiry_time, reminded FROM users")
        for uid, exp_str, reminded in cursor.fetchall():
            try:
                exp_dt = datetime.strptime(exp_str, '%Y-%m-%d %H:%M:%S')
                if now >= exp_dt:
                    try: await bot.send_message(uid, "❌ **Membership Expired!**\n\nAapki premium access khatam ho gayi hai.")
                    except: pass
                    cursor.execute("DELETE FROM users WHERE user_id=?", (uid,))
                elif now < exp_dt <= one_hour_later and reminded == 0:
                    try: await bot.send_message(uid, "⚠️ **EXPIRY REMINDER!**\n\nAapki membership **1 ghante** mein khatam hone wali hai.")
                    except: pass
                    cursor.execute("UPDATE users SET reminded=1 WHERE user_id=?", (uid,))
                conn.commit()
            except: pass
        await asyncio.sleep(600)

# --- START COMMAND ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    cursor.execute("INSERT OR IGNORE INTO all_users VALUES (?)", (user_id,))
    conn.commit()

    kb_fjoin = InlineKeyboardMarkup().add(InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK))
    kb_fjoin.add(InlineKeyboardButton("🔄 Verify / Start", callback_data="check_join"))
    fjoin_text = f"Hello {name}\n\nYou need to join in my Channel/Group to use me\n\nKindly Please join Channel."

    args = message.get_args()
    if args and args.startswith('file_'):
        cursor.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
        if not cursor.fetchone():
            try: return await bot.send_photo(user_id, IMG_FORCE_JOIN, caption=fjoin_text, reply_markup=kb_fjoin)
            except: return await message.answer(fjoin_text, reply_markup=kb_fjoin)
        
        f_key = args.replace('file_', '')
        cursor.execute("SELECT data FROM files WHERE file_id=?", (f_key,))
        res = cursor.fetchone()
        if res:
            msg = await message.answer(f"✅ Your Content: {res[0]}\n\n⚠️ Deleting in 10 mins.")
            asyncio.create_task(delete_after_delay(user_id, msg.message_id, 600))
        return

    kb_start = InlineKeyboardMarkup().add(InlineKeyboardButton("💎 BUY PREMIUM 💎", callback_data="buy_premium"))
    try: await bot.send_photo(user_id, IMG_START_MENU, caption=f"Hello {name}, Welcome!", reply_markup=kb_start)
    except: await message.answer(f"Hello {name}, Welcome!", reply_markup=kb_start)

# --- PREMIUM FLOW ---
@dp.callback_query_handler(lambda c: c.data == "buy_premium")
async def buy_step1(callback: types.CallbackQuery):
    name = callback.from_user.first_name
    text = f"👋 Hello {name}\n\n🎖️ Want Premium?\n\n› Choose a method below:\n\n• 💳 Pay with UPI (Instant activation)"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("💳 Pay with UPI", callback_data="pay_upi_list"))
    await callback.message.edit_caption(caption=text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "pay_upi_list")
async def show_plans(callback: types.CallbackQuery):
    text = (
        "✦ 𝗦𝗛𝗢𝗥𝗧𝗡𝗘𝗥 𝗣𝗟𝗔𝗡𝗦\nᴅᴜʀᴀᴛɪᴏɴ & ᴘʀɪᴄᴇ\n"
        "────────────────────\n"
        "›› 1 days : ₹20\n›› 7 Days : ₹50\n›› 15 days : ₹120\n›› 1 Months : ₹200\n"
        "❐ 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗠𝗘𝗧𝗛𝗢𝗗𝗦\n❐ 𝗉𝖺𝗒𝗍𝗆 • 𝗀𝗉𝖺𝗒 • 𝗉𝗁𝗈𝗇𝖾 𝗉𝖺𝗒 • 𝗎𝗉𝗂 𝖺𝗇𝖽 𝗊𝗋\n"
        "────────────────────\n"
        "✦ Pʀᴇᴍɪᴜᴍ ᴡɪʟʟ ʙᴇ ᴀᴅᴅᴇᴅ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴏɴᴄᴇ ᴘᴀɪᴅ\n"
        "✦ 𝗔𝗙𝗧𝗘𝗥 𝗣𝗔𝗬𝗠𝗘𝗡𝗧:\n"
        "❐ Sᴇɴᴅ ᴀ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ & ᴡᴀɪᴛ ᴀ ꜰᴇᴡ ᴍɪɴᴜᴛᴇꜱ ғᴏʀ ᴀᴄᴛɪᴠᴀᴛɪᴏɴ ✓"
    )
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("1 DAY", callback_data="pay_20_1"),
        InlineKeyboardButton("7 DAY", callback_data="pay_50_7"),
        InlineKeyboardButton("15 DAY", callback_data="pay_120_15"),
        InlineKeyboardButton("30 DAY", callback_data="pay_200_30")
    )
    await callback.message.edit_caption(caption=text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('pay_'))
async def send_qr(callback: types.CallbackQuery):
    _, price, days = callback.data.split('_')
    upi_url = f"upi://pay?pa={UPI_ID}&am={price}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_url}"
    qr_msg = await bot.send_photo(callback.from_user.id, qr_url, caption=f"💰 Amount: ₹{price}\n\n⚠️ QR deletes in 15 mins. Send screenshot after pay.")
    asyncio.create_task(delete_after_delay(callback.from_user.id, qr_msg.message_id, 900))

# --- SCREENSHOT & ADMIN ---
@dp.message_handler(content_types=['photo', 'text'])
async def handle_all(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMINS and message.text and ("t.me" in message.text or "http" in message.text):
        f_id = str(datetime.now().timestamp()).replace('.','')
        cursor.execute("INSERT INTO files VALUES (?, ?)", (f_id, message.text))
        conn.commit()
        return await message.answer(f"✅ Saved!\nLink: `https://t.me/{(await bot.get_me()).username}?start=file_{f_id}`")

    if message.photo:
        await message.answer("✅ premium membership Request Submitted!\n\n⚡ Your proof is being verified.\n📝 Status: Pending\n⏳ Time: 3 Hours (Max)")
        for adm in ADMINS:
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Approve 1 Day", callback_data=f"app_1_{user_id}"),
                InlineKeyboardButton("✅ Approve 30 Day", callback_data=f"app_30_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")
            )
            await bot.send_photo(adm, message.photo[-1].file_id, caption=f"Payment from {user_id}", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith(('app_', 'rej_')))
async def approval_logic(callback: types.CallbackQuery):
    data = callback.data.split('_')
    if data[0] == "app":
        days, uid = int(data[1]), data[2]
        exp = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT OR REPLACE INTO users (user_id, expiry_time, reminded) VALUES (?, ?, 0)", (uid, exp))
        conn.commit()
        await bot.send_message(uid, "✅ Pᴀʏᴍᴇɴᴛ Sᴜᴄᴄᴇssғᴜʟ!\n\n🎉 Pʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!\n💎 Eɴᴊᴏʏ ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss!")
    elif data[0] == "rej":
        await bot.send_message(data[1], "❌ Your payment proof was rejected. Please send a valid screenshot.")
    await callback.message.delete()
    await callback.answer("Done!")

@dp.callback_query_handler(lambda c: c.data == "check_join")
async def check_join_callback(callback: types.CallbackQuery):
    await callback.answer("Wait... bot is re-checking. Try /start again in 5s.", show_alert=True)

if __name__ == '__main__':
    keep_alive()
    loop = asyncio.get_event_loop()
    loop.create_task(expiry_checker())
    executor.start_polling(dp, skip_updates=True)
