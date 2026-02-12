from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from utils.crypto import decrypt_data
from datetime import datetime

async def send_scheduled_capsules(bot: Bot, db, girl_id):
    today = datetime.now().strftime('%Y-%m-%d')
    # НЕ ЗАБУДЬ добавь метод get_capsules_for_today в свой класс Database
    capsules = db.conn.cursor().execute(
        "SELECT id, file_id FROM capsules WHERE delivery_date = ?", (today,)
    ).fetchall()

    for cap_id, encrypted_file_id in capsules:
        try:
            file_id = decrypt_data(encrypted_file_id)
            await bot.send_voice(girl_id, file_id, caption="✨ Привет из прошлого! Послушай это.")
            # сносим нах
            db.conn.cursor().execute("DELETE FROM capsules WHERE id = ?", (cap_id,))
            db.conn.commit()
        except Exception as e:
            print(f"Ошибка доставки пасхалки: {e}")

def setup_scheduler(bot: Bot, db, girl_id):
    scheduler = AsyncIOScheduler()
    # чекап каждый день в 10:00
    scheduler.add_job(send_scheduled_capsules, 'cron', hour=10, args=[bot, db, girl_id])
    scheduler.start()