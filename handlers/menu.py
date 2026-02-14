from aiogram import Router, F, types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from ai_engine.model import AIEngine
from ai_engine.prompts import *
from db.sqlite import Database
from utils.weather import get_omsk_weather
from datetime import datetime
from aiogram.fsm.context import FSMContext
from main import AsyncIOScheduler


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

class MediationStates(StatesGroup):
    waiting_for_input = State()

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="✨ Тёплый импульс ✨"), types.KeyboardButton(text="🧸 Эхо близости 🧸"))
    builder.row(types.KeyboardButton(text="🧣 Мягкий мост 🧣"), types.KeyboardButton(text="😤 Дать пинка 😤"))
    builder.row(types.KeyboardButton(text="🤭 Игривый вызов 🤭"), types.KeyboardButton(text="🌌 Мост понимания 🌌"))
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
    await state.clear() # сброс
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

# 2. Обработка ситуации через ИИ
@router.message(MenuStates.waiting_for_choice_situation)
async def process_choice_situation(message: types.Message, state: FSMContext, ai: AIEngine):
    # Промпт, который заставляет ИИ думать как ты
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

@router.message(F.text == "🤭 Игривый вызов 🤭")
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
    
    # 1. Сохраняем сообщение в базу
    db.add_mediation_msg(user_id, user_role, message.text)
    
    # 2. Проверяем историю (последние сообщения)
    # Нам нужно понять, написал ли уже партнер
    history = db.get_mediation_history(limit=2) # Берем последние 2 сообщения
    
    # Если в истории только одно сообщение (текущее), значит партнер еще не высказался
    if len(history) < 2 or history[0][0] == history[1][0]:
        await message.answer("Я услышал тебя и сохранил твои чувства. Теперь я иду к партнеру, чтобы узнать его позицию. Как только он ответит — я вынесу решение.")
        
        # Уведомляем вторую половинку
        try:
            partner_name = "Серёжа" if partner_id == seryozha_id else "твоя любимая"
            await bot.send_message(
                partner_id, 
                f"❤️ !Мост понимания активирован! ❤️\n{user_role} хочет обсудить возникшую ситуацию. "
                "Пожалуйста, зайди в 'Мост понимания' и поделись своими чувствами, чтобы я мог вам помочь.",
                reply_markup=get_main_menu() # Чтобы человеку было удобно нажать кнопку
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление партнеру: {e}")
            
    else:
        # 3. Если оба высказались — запускаем ИИ
        await message.answer("Вторая сторона высказалась. Анализирую ваши сердца... Пожалуйста, подожди.")
        
        # Формируем историю для ИИ (берем побольше контекста для глубины)
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
        
        # Отправляем результат ОБОИМ
        result_text = "📝 **Мой анализ ситуации и путь к примирению:**\n\n" + analysis
        await bot.send_message(seryozha_id, result_text)
        await bot.send_message(angel_id, result_text)

    await state.clear()

@router.message(F.text == "✨ Тёплый импульс ✨")
async def warm_impulse(message: types.Message):
    builder = ReplyKeyboardBuilder()
    # Просто текст, без callback_data
    builder.row(types.KeyboardButton(text="🌱 Лёгкий 🌱"))
    builder.row(types.KeyboardButton(text="🔥 Средний 🔥"))
    builder.row(types.KeyboardButton(text="💥 Глубокий 💥"))
    builder.row(types.KeyboardButton(text="⬅️ Назад"))
    
    await message.answer(
        "Выбери интенсивность импульса:", 
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

@router.message(F.text.in_({"🌱 Лёгкий 🌱", "🔥 Средний 🔥", "💥 Глубокий 💥"}))
async def handle_impulse_text(message: types.Message, bot, seryozha_id: int):
    lvl = message.text
    
    # отправка админу
    await bot.send_message(seryozha_id, f"💓 Тёплый импульс от неё!\nИнтенсивность: {lvl}")

    await message.answer(
        f"Ты отправила {lvl} импульс. Серёжа уже в курсе! ❤️",
        reply_markup=get_main_menu() # здесь вызывай свою функцию главного меню
    )



@router.message(F.text == "🔔 Я в порядке 🔔")
async def handle_emergency(message: types.Message, bot, seryozha_id: int, angel_id: int):
    if message.from_user.id != angel_id:
        return
    
    await message.answer("Понял, передаю Серёже, что всё хорошо! ❤️")
    await bot.send_message(seryozha_id, "Она проверила связь. Всё хорошо.")



@router.message(F.text == "😤 Дать пинка 😤")
async def request_care(message: types.Message):
    builder = ReplyKeyboardBuilder()
    for btn in ["🤗 Просто обними (временно недоступно!) 🤗", "🕒 Внимания 🕒", "😤 Будь опорой 😤", "⬅️ Назад"]:
        builder.add(types.KeyboardButton(text=btn))
    builder.adjust(1, 1, 1, 1)
    await message.answer("Какая забота нужна?", reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text.in_({"🤗 Просто обними (временно недоступно!) 🤗", "🕒 Внимания 🕒", "😤 Будь опорой 😤"}))
async def handle_care(message: types.Message, bot, seryozha_id: int):
    await bot.send_message(seryozha_id, f"🆘 Ей нужна твоя забота: {message.text}")
    await message.answer("Запрос отправлен. ❤️", reply_markup=get_main_menu())



@router.message(F.text == "🧸 Эхо близости 🧸") # Можно переименовать кнопку в "Капсула моментов"
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
    
    # Логика определения времени (МСК)
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





@router.message(F.text == "🧣 Мягкий мост 🧣")
async def soft_bridge(message: types.Message):
    builder = ReplyKeyboardBuilder()
    for btn in ["☁️ Грустно ☁️", "🌪 Зла 🌪", "🫂 Обними позже(временно недоступно, к сожалению) 🫂", "🗣 Поговорим вечером 🗣", "⬅️ Назад"]:
        builder.add(types.KeyboardButton(text=btn))
    builder.adjust(2, 2, 1)
    await message.answer("Что на душе?", reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text.in_({"☁️ Грустно ☁️", "🌪 Зла 🌪", "🫂 Обними позже(временно недоступно, к сожалению) 🫂", "🗣 Поговорим вечером 🗣"}))
async def handle_bridge_selection(message: types.Message, state: FSMContext):
    await state.update_data(bridge_tone=message.text)
    await message.answer("Напиши причину (одним сообщением) или отправь '-', чтобы пропустить:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(MenuStates.waiting_for_bridge_reason)



@router.message(MenuStates.waiting_for_bridge_reason)
async def process_bridge_reason(message: types.Message, state: FSMContext):
    if message.text == "⬅️ Назад": # Обработка назад внутри состояния
        await state.clear()
        return await message.answer("Отменено", reply_markup=get_main_menu())

    reason = message.text if message.text != "-" else "без уточнений"
    await state.update_data(bridge_reason=reason)
    
    # Предлагаем варианты времени (по МСК девушки)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Сейчас"), types.KeyboardButton(text="Через 1 час"))
    builder.row(types.KeyboardButton(text="Через 2 часа"), types.KeyboardButton(text="Вечером (21:00 МСК)"))
    builder.row(types.KeyboardButton(text="⬅️ Назад"))
    
    await message.answer(
        "Когда Серёжа должен получить это сообщение? (Укажи время по твоему МСК или выбери вариант):",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(MenuStates.waiting_for_bridge_time)

@router.message(MenuStates.waiting_for_bridge_time)
async def process_bridge_time(message: types.Message, state: FSMContext, bot, seryozha_id: int, scheduler: AsyncIOScheduler):
    user_text = message.text
    data = await state.get_data()
    
    # Настройка таймзон
    moscow_tz = pytz.timezone('Europe/Moscow')
    omsk_tz = pytz.timezone('Asia/Omsk')
    
    now_moscow = datetime.now(moscow_tz)
    send_time = now_moscow

    # Логика выбора времени
    if "1 час" in user_text:
        send_time = now_moscow + timedelta(hours=1)
    elif "2 часа" in user_text:
        send_time = now_moscow + timedelta(hours=2)
    elif "21:00" in user_text:
        send_time = now_moscow.replace(hour=21, minute=0, second=0, microsecond=0)
        if send_time < now_moscow:
            send_time += timedelta(days=1)
    elif user_text == "Сейчас":
        send_time = now_moscow
    else:
        # Пытаемся распарсить ручной ввод (например "20:30")
        try:
            h, m = map(int, user_text.split(':'))
            send_time = now_moscow.replace(hour=h, minute=m, second=0, microsecond=0)
            if send_time < now_moscow: send_time += timedelta(days=1)
        except:
            if user_text != "⬅️ Назад":
                return await message.answer("Напиши время в формате ЧЧ:ММ (например 18:30)")

    # Пересчитываем в Омск для уведомления (просто для лога)
    send_time_omsk = send_time.astimezone(omsk_tz)
    
    final_text = (f"🌉 Мягкий мост...\n"
                  f"Состояние: {data['bridge_tone']}\n"
                  f"Причина: {data['bridge_reason']}\n"
                  f"🕒 Отправлено в {send_time.strftime('%H:%M')} по МСК")

    if user_text == "Сейчас":
        await bot.send_message(seryozha_id, final_text)
        await message.answer("Серёжа уже получил сообщение! ❤️", reply_markup=get_main_menu())
    else:
        # Планируем задачу
        scheduler.add_job(
            send_delayed_bridge,
            'date',
            run_date=send_time,
            args=[bot, seryozha_id, final_text]
        )
        await message.answer(
            f"Принято! Серёжа получит весточку в {send_time.strftime('%H:%M')} по твоему времени "
            f"(в Омске будет {send_time_omsk.strftime('%H:%M')}).",
            reply_markup=get_main_menu()
        )
    
    await state.clear()