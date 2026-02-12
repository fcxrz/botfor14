from aiogram import Router, Bot, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.crypto import encrypt_data
import os

router = Router()
ANGEL_ID = int(os.getenv("ANGEL_ID", 0))

class AdminStates(StatesGroup):
    waiting_for_girl_response = State()
    recording_capsule_voice = State()
    recording_capsule_context = State()

@router.message(Command("отклик"))
async def cmd_check_in(message: types.Message, bot: Bot, state: FSMContext):
    await bot.send_message(ANGEL_ID, "Серёжа спрашивает, всё ли ок? Расскажи парой слов.")
    await state.set_state(AdminStates.waiting_for_girl_response)
    await message.answer("Запрос отправлен. Ждём ответа...")

@router.message(AdminStates.waiting_for_girl_response)
async def process_girl_reply(message: types.Message, ai, bot: Bot, state: FSMContext, seryozha_id):
    if message.from_user.id != ANGEL_ID: return
    
    analysis = await ai.analyze_response(message.text)
    await bot.send_message(seryozha_id, f"Анализ состояния:\n{analysis}")
    await message.answer("Спасибо, я передала ему!")
    await state.clear()

@router.message(Command("пасхалка"))
async def cmd_capsule(message: types.Message, state: FSMContext):
    await message.answer("Запиши голосовое сообщение для будущего.")
    await state.set_state(AdminStates.recording_capsule_voice)

@router.message(AdminStates.recording_capsule_voice, F.voice)
async def process_voice(message: types.Message, state: FSMContext):
    await state.update_data(voice_id=message.voice.file_id)
    await message.answer("А теперь напиши контекст (что сейчас происходит, почему это важно?)")
    await state.set_state(AdminStates.recording_capsule_context)

@router.message(AdminStates.recording_capsule_context)
async def process_capsule_final(message: types.Message, state: FSMContext, ai, db):
    data = await state.get_data()
    intro = await ai.get_capsule_intro(message.text)
    
    # шифруемся
    encrypted_voice = encrypt_data(data['voice_id'])
    db.save_capsule(encrypted_voice, days=30)
    
    await message.answer(f"Готово! Через 30 дней я пришлю это сообщение с твоим вступлением:\n\n\"{intro}\"")
    await state.clear()