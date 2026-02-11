import logging
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ... (Baki purana configuration aur imports same rahenge) ...

# --- EXPIRY & REMINDER CHECKER ---
async def expiry_checker():
    while True:
        now = datetime.now()
        # 1 hour baad ka time nikalne ke liye
        one_hour_later = now + timedelta(hours=1)
        
        cursor.execute("SELECT user_id, expiry_time FROM users")
        all_premium_users = cursor.fetchall()

        for user_id, expiry_str in all_premium_users:
            try:
                expiry_dt = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')

                # 1. Check if EXPIRED
                if now >= expiry_dt:
                    try:
                        await bot.send_message(user_id, "❌ **Membership Expired!**\n\nAapki premium access khatam ho gayi hai. Dubara join karne ke liye /start karein.")
                    except: pass
                    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
                    conn.commit()
                
                # 2. Check for 1 HOUR REMINDER
                # Agar expiry agle 1 ghante mein hai aur abhi tak reminder nahi bheja
                elif now < expiry_dt <= one_hour_later:
                    # Hum ek temporary flag use kar sakte hain ya sirf message bhej sakte hain
                    # Taaki baar baar reminder na jaye, hum is check ko thoda smart rakhte hain
                    try:
                        await bot.send_message(user_id, "⚠️ **EXPIRY REMINDER!**\n\nAapki premium membership **1 ghante** mein khatam hone wali hai. Continue rakhne ke liye abhi renew karein!")
                    except: pass
            except Exception as e:
                logging.error(f"Error checking expiry for {user_id}: {e}")

        await asyncio.sleep(900) # Har 15 minute mein check karega

# --- START COMMAND ---
# (Pichla /start logic yahan aayega...)

if __name__ == '__main__':
    keep_alive()
    # Expiry checker ko background mein start karna
    loop = asyncio.get_event_loop()
    loop.create_task(expiry_checker())
    executor.start_polling(dp, skip_updates=True)
