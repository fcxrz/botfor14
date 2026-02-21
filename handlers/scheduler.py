from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from config import SERYOZHA_ID
from utils.crypto import decrypt_data
from datetime import datetime
from db.sqlite import Database

async def send_scheduled_capsules(bot: Bot, db, angel_id):
    today = datetime.now().strftime('%Y-%m-%d')
    # НЕ ЗАБУДЬ добавь метод get_capsules_for_today в свой класс DB
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
    # ищем капсулы, время которых пришло
    available = db.get_available_capsules()
    
    for cap_id, context, file_id in available:
        try:
            # пишем мне
            await bot.send_message(seryozha_id, f"📦 **Доступен новый момент из прошлого!**\nКонтекст: {context}")
            await bot.send_voice(seryozha_id, file_id)
            
            # помечаем как просмотренное, что бы не слать бесконечно
            db.mark_as_viewed(cap_id)
            
        except Exception as e:
            print(f"Ошибка при отправке капсулы {cap_id}: {e}")

async def check_hellsing_messages(bot: Bot, db: Database):
    # получаем сообщения, время которых пришло
    pending = db.get_pending_hellsings() 
    
    for h_id, recipient_id, from_chat_id, msg_id in pending:
        try:
            await bot.send_message(recipient_id, "🌑 Вам пришло сообщение «Хеллсинг» из прошлого... 🌑")
            await bot.copy_message(
                chat_id=recipient_id,
                from_chat_id=from_chat_id,
                message_id=msg_id
            )
            db.mark_hellsing_sent(h_id)
        except Exception as e:
            print(f"Ошибка при доставке Хеллсинга {h_id}: {e}")

def setup_scheduler(bot: Bot, db: Database, angel_id: int, seryozha_id: int, scheduler: AsyncIOScheduler):
    # ежеднев капсулы в 10
    scheduler.add_job(
        send_scheduled_capsules, 
        'cron', 
        hour=10, 
        args=[bot, db, angel_id]
    )
    
    # проверка обычных капсул раз в минуту
    scheduler.add_job(
        check_pending_capsules,
        "interval",
        minutes=1,
        args=[bot, db, seryozha_id] 
    )

    # проверка Хеллсинг-сообщений раз в минуту
    scheduler.add_job(
        check_hellsing_messages,
        "interval",
        minutes=1,
        args=[bot, db] # для Хеллсинга нужны только бот и база
    )