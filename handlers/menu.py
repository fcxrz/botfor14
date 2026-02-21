import random
from aiogram import Router, F, types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from ai_engine.model import AIEngine
from ai_engine.prompts import *
from db.sqlite import Database
from utils.weather import get_omsk_weather
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import pytz
from datetime import datetime, timedelta
from aiogram.fsm.state import StatesGroup, State

router = Router()

scheduler = AsyncIOScheduler()

class MenuStates(StatesGroup):
    waiting_for_bridge_reason = State()
    waiting_for_bridge_time = State()
    waiting_for_voice = State()
    waiting_for_context = State()
    waiting_for_unlock_time = State()
    waiting_for_choice_situation = State()
    waiting_for_pulse_type = State()
    waiting_for_pulse_text = State()
    # 21.02
    waiting_for_custom_kick = State()

class MediationStates(StatesGroup):
    waiting_for_input = State()

# новые стейты лучше создавать
class HellsingStates(StatesGroup):
    waiting_for_content = State()
    waiting_for_timeframe = State()
    waiting_for_custom_days = State()

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="✨ Тёплый импульс ✨"), types.KeyboardButton(text="🧸 Эхо близости 🧸"))
    builder.row(types.KeyboardButton(text="✉️ Сообщение Хеллсинг ✉️"), types.KeyboardButton(text="😤 Дать пинка 😤"))
    builder.row(types.KeyboardButton(text="🌆 Совместный вечер 🌆"), types.KeyboardButton(text="🌌 Мост понимания 🌌"))
    builder.row(types.KeyboardButton(text='🔔 Я в порядке 🔔'))
    builder.row(types.KeyboardButton(text="🤓 Верный выбор 🤓"))
    return builder.as_markup(resize_keyboard=True)

async def send_delayed_bridge(bot, chat_id: int, text: str):
    await bot.send_message(chat_id, text)

def get_time_of_day():
    hour = datetime.now().hour
    if 5 <= hour < 12: return "утро"
    if 12 <= hour < 18: return "день"
    if 18 <= hour < 23: return "вечер"
    return "ночь"

@router.message(F.text == "⬅️ Назад")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_menu())




@router.message(F.text == "🤓 Верный выбор 🤓")
async def start_choice_helper(message: types.Message, state: FSMContext):
    await message.answer(
        "🧐 Нужна помощь с выбором?\n"
        "Опиши ситуацию или варианты, между которыми ты выбираешь. "
        "Я проанализирую всё и подскажу, как бы поступил Серёжа.(необязательно)",
        reply_markup=ReplyKeyboardBuilder().row(types.KeyboardButton(text="⬅️ Назад")).as_markup(resize_keyboard=True)
    )
    await state.set_state(MenuStates.waiting_for_choice_situation)

@router.message(MenuStates.waiting_for_choice_situation)
async def process_choice_situation(message: types.Message, state: FSMContext, ai: AIEngine):
    # промпт, который заставляет ИИ думать как ты
    prompt = f"""
    Ты выступаешь в роли мудрого и любящего советника для девушки. Твой характер и логика основаны на ценностях её парня, Серёжи.
    
    СИТУАЦИЯ:
    {message.text}
    
    ЗАДАЧА:
    1. Дай конкретный совет, какой вариант выбрать.
    2. Ответ должен быть очень коротким (всего 2-3 предложения).
    3. Если нужно объяснение, пиши его через призму того, почему именно Серёжа посчитал бы этот выбор правильным для неё (например: "Я бы выбрал это, потому что хочу, чтобы ты меньше уставала").
    
    Пиши уверенно, но с любовью.
    """
    
    answer = await ai.generate(prompt)
    
    await message.answer(f"💡 **Мой совет:**\n\n{answer}", reply_markup=get_main_menu())
    await state.clear()

@router.message(F.text == "🌆 Совместный вечер 🌆")
async def handle_challenge(message: types.Message, ai: AIEngine, angel_id: int):
    if message.from_user.id != angel_id: 
        return
    
    print("--- Нажата кнопка Игривый вызов ---")
    
    # лутаем реальную погоду
    weather = await get_omsk_weather()
    print(f"Погода получена: {weather}")

    
    weekday = datetime.now().strftime('%A')
    time_of_day = get_time_of_day()
    print(f"Время получено: {time_of_day}")
    # переводим день недели на русский для ии
    days = {
        'Monday': 'Понедельник', 'Tuesday': 'Вторник', 'Wednesday': 'Среда',
        'Thursday': 'Четверг', 'Friday': 'Пятница', 'Saturday': 'Суббота', 'Sunday': 'Воскресенье'
    }
    weekday_ru = days.get(weekday, weekday)

    response = await ai.generate(
        TASK_CHALLENGE, 
        weather=weather, 
        weekday=weekday_ru,
        time=time_of_day
    )
    
    await message.answer(f"✨ {response}")
    print({response})

@router.message(F.text == "🌌 Мост понимания 🌌")
async def start_mediation(message: types.Message, state: FSMContext):
    await message.answer(
        "🧠 Режим медиатора активирован 🧠\n\n"
        "Напиши честно: что ты сейчас чувствуешь? В чем корень конфликта с твоей стороны?\n\n"
        "Я сохраню твои слова, запрошу позицию партнера и помогу вам найти общий язык.",
        reply_markup=ReplyKeyboardBuilder().row(types.KeyboardButton(text="⬅️ Назад")).as_markup(resize_keyboard=True)
    )
    await state.set_state(MediationStates.waiting_for_input)

@router.message(MediationStates.waiting_for_input)
async def process_mediation(message: types.Message, state: FSMContext, db: Database, ai: AIEngine, seryozha_id: int, angel_id: int, bot):
    user_id = message.from_user.id
    user_role = "Серёжа" if user_id == seryozha_id else "Она"
    partner_id = angel_id if user_id == seryozha_id else seryozha_id
    
    db.add_mediation_msg(user_id, user_role, message.text)
    
    # нам нужно понять, написал ли уже партнер
    history = db.get_mediation_history(limit=2) # берем последние 2 сообщения
    
    # если в истории только одно сообщение (текущее), значит партнер еще не высказался
    if len(history) < 2 or history[0][0] == history[1][0]:
        await message.answer("Я услышал тебя и сохранил твои чувства. Теперь я иду к партнеру, чтобы узнать его позицию. Как только он ответит — я вынесу решение.")
        
        # уведомляем вторую половинку
        try:
            partner_name = "Серёжа" if partner_id == seryozha_id else "твоя любимая"
            await bot.send_message(
                partner_id, 
                f"❤️ !Мост понимания активирован! ❤️\n{user_role} хочет обсудить возникшую ситуацию. "
                "Пожалуйста, зайди в 'Мост понимания' и поделись своими чувствами, чтобы я мог вам помочь.",
                reply_markup=get_main_menu()
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление партнеру: {e}")
            
    else:
        # если оба высказались — запускаем ИИ
        await message.answer("Вторая сторона высказалась. Анализирую ваши сердца... Пожалуйста, подожди.")
        
        # формируем историю для ИИ (берем побольше контекста)
        full_history = db.get_mediation_history(limit=10)
        formatted_history = "\n".join([f"{h[0]}: {h[1]}" for h in reversed(full_history)])

        prompt = f"""
        Ты — мудрый и глубокий психолог-медиатор. 
        Перед тобой два человека, которые любят друг друга, но сейчас запутались в эмоциях.
        
        ИСТОРИЯ ВАШЕГО ДИАЛОГА:
        {formatted_history}
        
        ТВОЯ ЗАДАЧА:
        1. Проанализируй скрытые чувства каждого (страх, потребность в защите, одиночество).
        2. Напиши развернутый ответ (минимум 4-5 абзацев).
        3. Обратись к обоим максимально тепло. 
        4. Стань мостом: объясни Серёже боль Её, а Ей — уязвимость Серёжи.
        5. Найди точку соприкосновения и предложи мудрое решение.
        
        Пиши художественно, используй метафоры. Твой текст должен лечить.
        """
        
        analysis = await ai.generate(prompt)
        
        # отправляем результат ОБОИМ
        result_text = "📝 **Мой анализ ситуации и путь к примирению:**\n\n" + analysis
        await bot.send_message(seryozha_id, result_text)
        await bot.send_message(angel_id, result_text)

    await state.clear()

@router.message(F.text == "✨ Тёплый импульс ✨")
async def warm_impulse(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🌱 Лёгкий 🌱"))
    builder.row(types.KeyboardButton(text="🔥 Средний 🔥"))
    builder.row(types.KeyboardButton(text="💥 Глубокий 💥"))
    builder.row(types.KeyboardButton(text="⬅️ Назад"))
    
    await state.set_state(MenuStates.waiting_for_pulse_type)
    await message.answer(
        "Выбери интенсивность импульса:", 
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@router.message(MenuStates.waiting_for_pulse_type, F.text.in_(["💥 Глубокий 💥", "🔥 Средний 🔥", "🌱 Лёгкий 🌱"]))
async def process_pulse_type(message: types.Message, state: FSMContext):
    await state.update_data(pulse_type=message.text)

    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text = "⬅️ Назад"))

    await state.set_state(MenuStates.waiting_for_pulse_text)
    await message.answer(
        f"Сила: {message.text}\nЧто напишем в дополнение?\n"
        "(Напиши текст или отправь '-', чтобы отправить только импульс)",
        reply_markup=ReplyKeyboardBuilder().row(types.KeyboardButton(text="⬅️ Назад")).as_markup(resize_keyboard=True)
    )

@router.message(MenuStates.waiting_for_pulse_text)
async def process_pulse_final(message: types.Message, state: FSMContext, bot, seryozha_id: int):
    data = await state.get_data()
    pulse_type = data.get("pulse_type")
    
    # усли ввел "-", подставляем фразу
    user_text = message.text if message.text != "-" else "Ангелина просто шлет тебе свое тепло."

    msg_to_her = (
        f"🧨 ТЕБЕ ПРИЛЕТЕЛ {pulse_type} ИМПУЛЬС ✨\n\n"
        f"💬 Сообщение: _{user_text}_\n\n"
        "✨ Почувствуй это тепло прямо сейчас."
    )
    
    try:
        await message.bot.send_message(seryozha_id, msg_to_her, parse_mode="Markdown") 
        await message.answer("✅ Импульс доставлен в самое сердце!", reply_markup=get_main_menu())
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {(str(e))}")
    

@router.message(F.text == "⬅️ Назад")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear() # сброс
    await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_menu())



@router.message(F.text == "🔔 Я в порядке 🔔")
async def handle_emergency(message: types.Message, bot, seryozha_id: int, angel_id: int):
    if message.from_user.id != angel_id:
        return
    
    await message.answer("Понял, передаю Серёже, что всё хорошо! ❤️")
    await bot.send_message(seryozha_id, "Она проверила связь. Всё хорошо.")



@router.message(F.text == "😤 Дать пинка 😤")
async def request_kick(message: types.Message):
    builder = ReplyKeyboardBuilder()
    buttons = [
        "🗣 Хочу диалог, но не знаю как начать",
        "🧨 Просто сильно пнуть!",
        "❤️ Мне больно, но я не хочу тебя терять",
        "✏️ Свой вариант (текст/ГС/видео)",
        "⬅️ Назад"
    ]
    for btn in buttons:
        builder.add(types.KeyboardButton(text=btn))
    builder.adjust(1) # Все кнопки в один столбец для удобства
    
    await message.answer(
        "Выбери способ сделать шаг навстречу или отправь что-то своё:", 
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@router.message(F.text.in_({
    "🗣 Хочу диалог, но не знаю как начать",
    "🧨 Просто сильно пнуть!",
    "❤️ Мне больно, но я не хочу тебя терять"
}))
async def handle_predefined_kick(message: types.Message, bot, seryozha_id: int):
    await bot.send_message(seryozha_id, f"⚡️ **Тебе прилетел «ПинОк»!**\n\nОна говорит: {message.text}")
    await message.answer("Твой сигнал услышан. Спасибо тебе. ❤️", reply_markup=get_main_menu())

@router.message(F.text == "✏️ Свой вариант (текст/ГС/видео)")
async def start_custom_kick(message: types.Message, state: FSMContext):
    await message.answer(
        "Я готов. Пришли мне текст, запиши ГС, видео или отправь фото.\n"
        "Я передам это Серёже как твой искренний порыв.",
        reply_markup=ReplyKeyboardBuilder().row(types.KeyboardButton(text="⬅️ Назад")).as_markup(resize_keyboard=True)
    )
    await state.set_state(MenuStates.waiting_for_custom_kick)

@router.message(MenuStates.waiting_for_custom_kick)
async def process_custom_kick(message: types.Message, state: FSMContext, bot, seryozha_id: int):

    await bot.send_message(seryozha_id, "⚡️ Тебе прилетел особенный «ПинОк»!\nЛови послание:")

    await message.copy_to(chat_id=seryozha_id)
    
    await message.answer("Твоё послание доставлено. Ты молодец, что решилась. ❤️", reply_markup=get_main_menu())
    await state.clear()



@router.message(F.text == "🧸 Эхо близости 🧸") # можно переименовать кнопку в "Капсула моментов"
async def start_capsule(message: types.Message, state: FSMContext):
    await message.answer(
        "🎙 **Создаём новый момент.**\nЗапиши голосовое сообщение, которое я сохраню для Серёжи.",
        reply_markup=ReplyKeyboardBuilder().row(types.KeyboardButton(text="⬅️ Назад")).as_markup(resize_keyboard=True)
    )
    await state.set_state(MenuStates.waiting_for_voice)

@router.message(MenuStates.waiting_for_voice, F.voice)
async def process_capsule_voice(message: types.Message, state: FSMContext):
    await state.update_data(voice_id=message.voice.file_id)
    await message.answer("📝 Теперь напиши коротко, о чем это сообщение? (Контекст)")
    await state.set_state(MenuStates.waiting_for_context)

@router.message(MenuStates.waiting_for_context)
async def process_capsule_context(message: types.Message, state: FSMContext):
    await state.update_data(context=message.text)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Сразу"), types.KeyboardButton(text="Завтра"))
    builder.row(types.KeyboardButton(text="Через неделю"), types.KeyboardButton(text="⬅️ Назад"))
    
    await message.answer(
        "🔒 Когда Серёжа сможет это прослушать?\n(Выбери вариант или напиши дату ДД.ММ.ГГГГ)",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(MenuStates.waiting_for_unlock_time)

@router.message(MenuStates.waiting_for_unlock_time)
async def process_capsule_final(message: types.Message, state: FSMContext, db: Database, angel_id: int):
    data = await state.get_data()
    text = message.text
    
    # логика определения времени (МСК)
    moscow_tz = pytz.timezone('Europe/Moscow')
    unlock_at = datetime.now(moscow_tz)

    if text == "Завтра":
        unlock_at += timedelta(days=1)
    elif text == "Через неделю":
        unlock_at += timedelta(days=7)
    elif text != "Сразу":
        try:
            unlock_at = datetime.strptime(text, "%d.%m.%Y").replace(tzinfo=moscow_tz)
        except:
            return await message.answer("Используй формат ДД.ММ.ГГГГ (например 20.05.2026)")

    db.save_capsule(angel_id, data['voice_id'], data['context'], unlock_at)
    
    await message.answer(
        f"✅ Момент сохранен!\nКонтекст: {data['context']}\nБудет доступен: {unlock_at.strftime('%d.%m.%Y')}",
        reply_markup=get_main_menu()
    )
    await state.clear()






async def save_hellsing_to_db(message: types.Message, state: FSMContext, db: Database, seconds_limit: int, seryozha_id: int, angel_id: int, is_test=False):
    data = await state.get_data()
    now = datetime.now()
    

    if is_test:
        send_at = now + timedelta(seconds=seconds_limit) 
    # cчитаем случайный момент: от 10 минут до указанного лимита
    else:
        safe_limit = max(601, seconds_limit)
        random_seconds = random.randint(600, safe_limit)
        send_at = now + timedelta(seconds=random_seconds)
    
    recipient_id = angel_id if message.from_user.id == seryozha_id else seryozha_id
    
    db.add_hellsing(
        sender_id=message.from_user.id,
        recipient_id=recipient_id,
        chat_id=data['chat_id'],
        msg_id=data['msg_id'],
        send_at=send_at
    )
    
    await message.answer(
        f"🎯 Цель захвачена 🎯\n"
        f"Я спрятал твоё послание. Оно детонирует в случайный момент до `{send_at.strftime('%d.%m.%Y %H:%M')}`.\n"
        "Никто не знает, когда это случится. Даже я.", 
        reply_markup=get_main_menu()
    )
    await state.clear()

@router.message(F.text == "✉️ Сообщение Хеллсинг ✉️")
async def start_hellsing(message: types.Message, state: FSMContext):
    await message.answer(
        "🧛 Протокол Хеллсинг запущен 🧛\n\n"
        "Пришли мне то, что я должен доставить (текст, ГС, видео, фото). "
        "Я спрячу это и подброшу партнеру в самый неожиданный момент.",
        reply_markup=ReplyKeyboardBuilder().row(types.KeyboardButton(text="⬅️ Назад")).as_markup(resize_keyboard=True)
    )
    await state.set_state(HellsingStates.waiting_for_content)

@router.message(HellsingStates.waiting_for_content)
async def process_hellsing_content(message: types.Message, state: FSMContext):
    # cохраняем ID сообщения и чата
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)
    
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🧪 Тест (5 минут)"))
    builder.row(types.KeyboardButton(text="❓ Свое время ❓"))
    builder.row(types.KeyboardButton(text="🕰️ В этом месяце 🕰️"))
    builder.row(types.KeyboardButton(text="📅 В этом году 📅"))
    builder.row(types.KeyboardButton(text="⬅️ Назад"))
    
    await message.answer("В какой период времени мне совершить атаку?", reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(HellsingStates.waiting_for_timeframe)

@router.message(HellsingStates.waiting_for_timeframe)
async def process_hellsing_time(message: types.Message, state: FSMContext, db: Database, seryozha_id: int, angel_id: int):

    now = datetime.now()
    seconds_limit = 0
    
    if message.text == "🕰️ В этом месяце 🕰️":
        seconds_limit = 30 * 24 * 60 * 60
    elif message.text == "🧪 Тест (5 минут)":
        seconds_limit = 300 
        await save_hellsing_to_db(message, state, db, seconds_limit, seryozha_id, angel_id, is_test=True)
        return
    elif message.text == "📅 В этом году 📅":
        seconds_limit = 365 * 24 * 60 * 60
    elif message.text == "❓ Свое время ❓":
        await message.answer("На сколько дней максимум я могу отложить это послание? (Введи число дней, например: 7 или 150)")
        await state.set_state(HellsingStates.waiting_for_custom_days)
        return

    await save_hellsing_to_db(message, state, db, seconds_limit, seryozha_id, angel_id)

@router.message(HellsingStates.waiting_for_custom_days)
async def process_custom_days(message: types.Message, state: FSMContext, db: Database, seryozha_id: int, angel_id: int):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи только число (количество дней).")
        return

    days = int(message.text)
    if days <= 0:
        await message.answer("Число должно быть больше нуля.")
        return

    seconds_limit = days * 24 * 60 * 60
    await save_hellsing_to_db(message, state, db, seconds_limit, seryozha_id, angel_id)