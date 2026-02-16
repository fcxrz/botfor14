from aiogram import Router, Bot, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandObject
from db.sqlite import Database
from handlers.menu import get_main_menu
from utils.crypto import encrypt_data
import os

router = Router()
ANGEL_ID = int(os.getenv("ANGEL_ID", 0))


class AdminStates(StatesGroup):
    waiting_for_girl_response = State()
    recording_capsule_voice = State()
    recording_capsule_context = State()
    waiting_for_pulse_type = State()
    waiting_for_pulse_text = State()

def get_pulse_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="💥 Глубокий 💥"))
    builder.row(types.KeyboardButton(text="🔥 Средний 🔥"))
    builder.row(types.KeyboardButton(text="🌱 Лёгкий 🌱"))
    builder.row(types.KeyboardButton(text="⬅️ Назад"))
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("импульс"))
async def cmd_pulse_start(message: types.Message, state: FSMContext, seryozha_id: int):
    if message.from_user.id != seryozha_id:
        return
    
    await message.answer("Выбери силу импульса для неё:", reply_markup=get_pulse_keyboard())
    await state.set_state(AdminStates.waiting_for_pulse_type)

# Обработка выбора силы
@router.message(AdminStates.waiting_for_pulse_type, F.text.in_(["💥 Глубокий 💥", "🔥 Средний 🔥", "🌱 Лёгкий 🌱"]))
async def process_pulse_type(message: types.Message, state: FSMContext):
    await state.update_data(pulse_type=message.text)
    await message.answer(
        f"Сила: {message.text}\nЧто напишем в дополнение?\n"
        "(Напиши текст или отправь '-', чтобы отправить только импульс)",
        reply_markup=ReplyKeyboardBuilder().row(types.KeyboardButton(text="⬅️ Назад")).as_markup(resize_keyboard=True)
    )
    await state.set_state(AdminStates.waiting_for_pulse_text)

@router.message(AdminStates.waiting_for_pulse_text)
async def process_pulse_final(message: types.Message, state: FSMContext, bot: Bot, angel_id: int):
    data = await state.get_data()
    pulse_type = data.get("pulse_type")
    
    # усли ввел "-", подставляем красвую стандартную фразу
    user_text = message.text if message.text != "-" else "Серёжа просто шлет тебе свое тепло."

    msg_to_her = (
        f"🧨 ТЕБЕ ПРИЛЕТЕЛ {pulse_type} ИМПУЛЬС ✨\n\n"
        f"💬 Сообщение: _{user_text}_\n\n"
        "✨ Почувствуй это тепло прямо сейчас."
    )
    
    try:
        await bot.send_message(angel_id, msg_to_her, parse_mode="Markdown")
        await message.answer("✅ Импульс доставлен в самое сердце!", reply_markup=types.ReplyKeyboardRemove())
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить (возможно, бот заблокирован): {e}")
    
    await state.clear()

@router.message(F.text == "⬅️ Назад")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear() # сброс
    await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_menu())

@router.message(Command("отклик"))
async def cmd_check_in(message: types.Message, bot: Bot, state: FSMContext, angel_id: int):
    try:
        await bot.send_message(angel_id, "Серёжа спрашивает, всё ли ок? Нажми на кнопочку 'Я в порядке' снизу! Или напиши ему лично: https://t.me/pcxrz")
        await state.set_state(AdminStates.waiting_for_girl_response)
        await message.answer("Запрос отправлен. Ждём ответа...")
        print("Запрос отправлен. Ждём ответа...")
    except Exception as e:
        await message.answer(f"Ошибка: не могу найти чат с девушкой. Она нажала /start?")
    

@router.message(AdminStates.waiting_for_girl_response)
async def process_girl_reply(message: types.Message, ai, bot: Bot, state: FSMContext, seryozha_id):
    if message.from_user.id != ANGEL_ID: return
    
    analysis = await ai.analyze_response(message.text)
    await bot.send_message(seryozha_id, f"Анализ состояния:\n{analysis}")
    await message.answer("Спасибо, я передала ему!")
    await state.clear()


@router.message(Command("моменты"))
async def list_moments(message: types.Message, db: Database, seryozha_id: int):
    if message.from_user.id != seryozha_id: return

    available = db.get_available_capsules()
    if not available:
        await message.answer("📭 Пока новых доступных моментов нет. Подожди, пока время разблокировки наступит!")
        return

    for m_id, context, file_id in available:
        await message.answer(f"📦 Доступен момент: {context}")
        await message.answer_voice(file_id)
        # Опционально: db.mark_as_viewed(m_id) — чтобы не слать одно и то же дважды




# ПОХУЙ
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

