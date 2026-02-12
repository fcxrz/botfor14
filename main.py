import asyncio
import os
from handlers import admin, scheduler
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from db.sqlite import Database
from ai_engine.model import AIEngine
from handlers import menu


# В Railway добавьте TELEGRAM_BOT_TOKEN в Variables
TOKEN = os.getenv("8376471127:AAFHrRVWR1nFnq9kbvql5NUxxk_ER4AQHIQ")
SERYOZHA_ID = 574403009 # ваш айдишник (или старт въебите прост)
ANGEL_ID = 7911098627 # айдишник любимой

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    db = Database()
    ai = AIEngine()

    # Проброс зависимостей в хендлеры
    dp["db"] = db
    dp["ai"] = ai
    dp["seryozha_id"] = SERYOZHA_ID

    @dp.message(Command("start"))
    async def start(message: types.Message):
        if message.from_user.id == SERYOZHA_ID:
            db.set_user(message.from_user.id, "admin")
            await message.answer("Привет, Серёжа! Твои команды: /отклик, /пасхалка")
        else:
            db.set_user(message.from_user.id, "girl")
            await message.answer("Привет! Я твой эмоциональный мост.", reply_markup=menu.main_menu())

    dp.include_router(menu.router)
    
    scheduler.setup_scheduler(bot, db, ANGEL_ID)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())