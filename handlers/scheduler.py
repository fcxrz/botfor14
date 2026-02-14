from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from main import SERYOZHA_ID
from utils.crypto import decrypt_data
from datetime import datetime
from db.sqlite import Database

async def send_scheduled_capsules(bot: Bot, db, angel_id):
    today = datetime.now().strftime('%Y-%m-%d')
    # НЕ ЗАБУДЬ добавь метод get_capsules_for_today в свой класс Database
    capsules = db.conn.cursor().execute(
        "SELECT id, file_id FROM capsules WHERE delivery_date = ?", (today,)
    ).fetchall()

    for cap_id, encrypted_file_id in capsules:
        try:
            file_id = decrypt_data(encrypted_file_id)
            await bot.send_voice(angel_id, file_id, caption="✨ Привет из прошлого! Послушай это.")
            # сносим нах
            db.conn.cursor().execute("DELETE FROM capsules WHERE id = ?", (cap_id,))
            db.conn.commit()
        except Exception as e:
            print(f"Ошибка доставки пасхалки: {e}")

async def check_pending_capsules(bot: Bot, db: Database, seryozha_id: int):
    # Ищем капсулы, время которых пришло
    available = db.get_available_capsules()
    
    for cap_id, context, file_id in available:
        try:
            # 1. Пишем Серёже
            await bot.send_message(seryozha_id, f"📦 **Доступен новый момент из прошлого!**\nКонтекст: {context}")
            await bot.send_voice(seryozha_id, file_id)
            
            # 2. Помечаем как просмотренное, чтобы не слать бесконечно
            db.mark_as_viewed(cap_id)
            
        except Exception as e:
            print(f"Ошибка при отправке капсулы {cap_id}: {e}")

def setup_scheduler(bot, db, angel_id, seryozha_id, scheduler):
    scheduler = AsyncIOScheduler()
    # чекап каждый день в 10:00
    scheduler.add_job(send_scheduled_capsules, 'cron', hour=10, args=[bot, db, angel_id])
    scheduler.start()

    from .scheduler import check_pending_capsules # Импорт внутри, если функция ниже
    
    scheduler.add_job(
        check_pending_capsules,
        "interval",
        minutes=1,
        args=[bot, db, seryozha_id]
    )
