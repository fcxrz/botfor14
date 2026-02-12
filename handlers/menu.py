from aiogram import Router, F, types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from ai_engine.model import AIEngine
from ai_engine.prompts import TASK_CHALLENGE
from utils.weather import get_omsk_weather
from datetime import datetime

router = Router()

def main_menu():
    builder = ReplyKeyboardBuilder()
    buttons = ["Тёплый импульс", "Эхо близости", "Мягкий мост", 
               "Запросить заботу", "Игривый вызов", "Благодарность", "Я в порядке"]
    for btn in buttons: builder.button(text=btn)
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@router.message(F.text == "Игривый вызов")
async def handle_challenge(message: types.Message, ai: AIEngine):
    weather = get_omsk_weather()
    weekday = datetime.now().strftime("%A")
    time_of_day = "вечер"
    
    challenge = ai.generate(TASK_CHALLENGE, weekday=weekday, weather=weather, time=time_of_day)
    await message.answer(f"✨ Твой вызов на сегодня:\n\n{challenge}")

@router.message(F.text == "Я в порядке")
async def handle_emergency(message: types.Message, bot, seryozha_id):
    await message.answer("Поняла, передаю Серёже, что всё хорошо! ❤️")
    await bot.send_message(seryozha_id, "Она проверила связь. Всё хорошо.")