import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION (Aapki Details) ---
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
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_time TIMESTAMP, plan_type TEXT)''')
conn.commit()

# --- HELPER FUNCTIONS ---
def get_setting(key, default):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else default

def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

# --- EXPIRY CHECKER ---
async def expiry_checker():
    while True:
        now = datetime.now()
        one_hour_later = now + timedelta(hours=1)
        
        # 1 Hour Reminder
        cursor.execute("SELECT user_id FROM users WHERE expiry_time <= ? AND expiry_time > ?", (one_hour_later, now))
        for user in cursor.fetchall():
            try: await bot.send_message(user[0], "››⚠️ Reminder: Your premium membership will expire in 1 hour.\nTo renew your premium membership, please Contact Our Admins.")
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

# --- START FLOW ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    f_join = get_setting('f_join', 'None')
    
    if f_join != 'None':
        try:
            member = await bot.get_chat_member(f_join, user_id)
            if member.status == 'left':
                kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Join Channel", url=f"https://t.me/{f_join.replace('@','')}"))
                return await message.answer(f"Pehle {f_join} join karein!", reply_markup=kb)
        except: pass

    cursor.execute("SELECT expiry_time FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        target = get_setting('target_link', 'Link Not Set')
        await message.answer(f"✅ Your Premium is Active!\n\n🔗 Private Link: {target}")
    else:
        p1, p2 = get_setting('p_day', '20'), get_setting('p_month', '200')
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton(f"1 Day - ₹{p1}", callback_data="buy_1d"),
            InlineKeyboardButton(f"1 Month - ₹{p2}", callback_data="buy_1m")
        )
        await message.answer("Select a Premium Plan:", reply_markup=kb)

# --- PAYMENT CAPTION ---
@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def pay_proc(callback_query: types.CallbackQuery):
    plan = "1 Day" if "1d" in callback_query.data else "1 Month"
    amt = get_setting('p_day' if "1d" in callback_query.data else 'p_month', '20')
    
    upi_url = f"upi://pay?pa={UPI_ID}&am={amt}&tn=Premium"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={upi_url}"
    
    caption = (f"✦ 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗣𝗔𝗬𝗠𝗘𝗡𝗧\n\n❐ Aᴍᴏᴜɴᴛ: ₹ {amt}\n≡ Vᴀʟɪᴅɪᴛʏ: {plan}\n"
               f"────────────────────\n≡ ❐ 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗠𝗘𝗧𝗛𝗢𝗗𝗦\n❐ 𝗉𝖺𝗒𝗍𝗆 • 𝗀𝗉𝖺𝗒 • 𝗉𝗁𝗈𝗇𝖾 𝗉𝖺𝗒 • 𝗎𝗉𝗂 𝖺𝗇𝖽 𝗊𝗋\n\n"
               f"✦ 𝗔𝗙𝗧𝗘𝗥 𝗣𝗔𝗬𝗠𝗘𝗡𝗧:\n❐ Sᴇɴᴅ ᴀ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ")
    await bot.send_photo(callback_query.from_user.id, qr_url, caption=caption)

# --- PHOTO HANDLER ---
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    await message.answer("✅ premium membership Request Submitted!\n\n⚡ Your proof is being verified.\n📝 Status: Pending\n⏳ Time: 3 Hours (Max)\n\n🟢 You will be notified automatically once funds are added.")
    for admin in ADMINS:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Approve 1 Day ✅", callback_data=f"app_1d_{message.from_user.id}"),
            InlineKeyboardButton("Approve 1 Month ✅", callback_data=f"app_1m_{message.from_user.id}"),
            InlineKeyboardButton("Reject ❌", callback_data=f"rej_{message.from_user.id}")
        )
        await bot.send_photo(admin, message.photo[-1].file_id, caption=f"New Payment from {message.from_user.id}", reply_markup=kb)

# --- ADMIN ACTION ---
@dp.callback_query_handler(lambda c: c.data.startswith(('app_', 'rej_')))
async def admin_act(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMINS: return
    act, plan, uid = callback_query.data.split('_')
    if act == 'app':
        days = 1 if plan == '1d' else 30
        expiry = datetime.now() + timedelta(days=days)
        cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (uid, expiry, plan))
        conn.commit()
        msg = (f"✅ Pᴀʏᴍᴇɴᴛ Sᴜᴄᴄᴇssғᴜʟ!\n\n🎉 Pʀᴇᴍɪᴜᴍ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ғᴏʀ {days} day!\n💎 Eɴᴊᴏʏ ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss!")
        await bot.send_message(uid, msg)
        await callback_query.answer("User Activated!")
    else:
        await bot.send_message(uid, "❌ Payment Rejected. Please send valid proof.")
        await callback_query.answer("Rejected!")

# --- ADMIN COMMANDS ---
@dp.message_handler(commands=['admin'])
async def admin_p(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("🛠 Admin Panel:\n/setprice_day [Rs]\n/setprice_month [Rs]\n/setlink [Link]\n/setchannel [@channel]")

@dp.message_handler(commands=['setprice_day', 'setprice_month', 'setlink', 'setchannel'])
async def updates(message: types.Message):
    if message.from_user.id not in ADMINS: return
    cmd, val = message.get_command(), message.get_args()
    if not val: return await message.answer("Value bhi likhein!")
    if 'day' in cmd: set_setting('p_day', val)
    elif 'month' in cmd: set_setting('p_month', val)
    elif 'link' in cmd: set_setting('target_link', val)
    elif 'channel' in cmd: set_setting('f_join', val)
    await message.answer("Updated! ✅")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(expiry_checker())
    executor.start_polling(dp, skip_updates=True)
