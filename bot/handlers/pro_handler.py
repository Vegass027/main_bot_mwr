from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest

from bot.keyboards.keyboards import (
    get_personalization_menu,
    get_back_to_pro_menu,
    get_back_to_personalization,
    get_pro_menu
)
from bot.services.user_service import UserService
from bot.utils.states import UserStates

router = Router()

@router.callback_query(F.data == "personalization")
async def personalization_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Меню персонализации воронки"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    menu_text = """🎨 **Конструктор Твоей Воронки**

Здесь ты можешь заменить стандартные тексты бота на свой живой голос. Это повышает конверсию в регистрацию в 3 раза!

Выбери этап для записи:"""
    
    try:
        await callback.message.edit_text(
            menu_text,
            reply_markup=get_personalization_menu(
                has_welcome=bool(user.welcome_video_id),
                has_passive_income=bool(user.voice_passive_income_id),
                has_travel=bool(user.voice_free_travel_id),
                has_freedom=bool(user.voice_freedom_id),
                has_final=bool(user.voice_final_cta_id)
            ),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Меню персонализации", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.personalization_menu)
    await callback.answer()

# Обработчик приветствия (видео-кружок)
@router.callback_query(F.data == "upload_welcome_video")
async def upload_welcome_video_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку приветственного видео"""
    
    prompt_text = """📹 **Приветствие (Видео-кружок)**

Запиши Видео-сообщение (Кружочек).
Это первое, что увидит человек после нажатия 'Старт'.

📝 **Сценарий:**

• Поздоровайся и назови имя.
• Скажи: _'Я использую этот сервис, чтобы путешествовать роскошно и зарабатывать на этом'_.
• Призыв: _'Жми кнопку внизу и выбери, что тебе интереснее — экономия или бизнес'_.

⏳ **Жду твой кружочек...**"""
    
    try:
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_back_to_personalization(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Запись приветствия", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_welcome_video)
    await callback.answer()

@router.message(UserStates.awaiting_welcome_video, F.video_note)
async def save_welcome_video(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение приветственного видео"""
    
    telegram_id = str(message.from_user.id)
    video_id = message.video_note.file_id
    
    await UserService.update_welcome_video(session, telegram_id, video_id)
    
    await message.answer_video_note(video_note=video_id)
    await message.answer(
        "✅ **Готово! Приветствие сохранено.**\n\n"
        "Теперь все твои новые рефералы увидят это при старте.",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_welcome_video)
async def wrong_welcome_video_type(message: Message):
    """Обработка неверного типа контента для видео"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **видео-кружочек**.\n\n"
        "Чтобы записать:\n"
        "1. Нажми на скрепку\n"
        "2. Выбери 'Видеосообщение'\n"
        "3. Запиши приветствие",
        parse_mode="Markdown"
    )

# Обработчик ветки "Деньги" (голосовое)
@router.callback_query(F.data == "upload_passive_income_voice")
async def upload_passive_income_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку голосового для ветки Деньги"""
    
    prompt_text = """💸 **Ветка: Деньги**

Запиши Голосовое сообщение для тех, кто выбрал 'Пассивный доход'.
Бот отправит его сразу после факта про $8.8 Трлн рынка.

📝 **Сценарий:**
_'Слушай, я сам пришел сюда именно за деньгами. Я устал от рискованных тем. Здесь понятный продукт — люди всегда будут летать в отпуск. Я посчитал цифры: даже крошечный процент от этого рынка — это огромный капитал. Давай покажу схему.'_

⏳ **Жду голосовое...**"""
    
    try:
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_back_to_personalization(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Запись 'Деньги'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_passive_income_voice)
    await callback.answer()

@router.message(UserStates.awaiting_passive_income_voice, F.voice)
async def save_passive_income_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение голосового для ветки Деньги"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_passive_income(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Голосовое для ветки 'Деньги' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_passive_income_voice)
async def wrong_passive_income_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик ветки "Путешествия" (голосовое)
@router.callback_query(F.data == "upload_travel_voice")
async def upload_travel_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку голосового для ветки Путешествия"""
    
    prompt_text = """🌍 **Ветка: Путешествия**

Запиши Голосовое сообщение для тех, кто хочет 'Путешествовать бесплатно'.

📝 **Сценарий:**
_'Раньше я думал, что отели 5 звезд — это дорого. Но когда я увидел оптовые цены... это шок. Зачем переплачивать Букингу? Плюс, здесь можно накапливать баллы и летать вообще бесплатно. Жми кнопку, я покажу реальные примеры экономии.'_

⏳ **Жду голосовое...**"""
    
    try:
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_back_to_personalization(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Запись 'Путешествия'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_travel_voice)
    await callback.answer()

@router.message(UserStates.awaiting_travel_voice, F.voice)
async def save_travel_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение голосового для ветки Путешествия"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_travel(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Голосовое для ветки 'Путешествия' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_travel_voice)
async def wrong_travel_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик ветки "Свобода" (голосовое)
@router.callback_query(F.data == "upload_freedom_voice")
async def upload_freedom_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку голосового для ветки Свобода"""
    
    prompt_text = """🚀 **Ветка: Свобода**

Запиши Голосовое сообщение для тех, кто хочет 'Уволиться из найма'.

📝 **Сценарий:**
_'Я прекрасно понимаю чувство, когда живешь от выходных до выходных. Этот бизнес хорош тем, что его можно строить параллельно с работой, в телефоне. Это твой запасной аэродром, который скоро станет основным. Посмотри план, как выйти на $2000.'_

⏳ **Жду голосовое...**"""
    
    try:
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_back_to_personalization(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Запись 'Свобода'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_freedom_voice)
    await callback.answer()

@router.message(UserStates.awaiting_freedom_voice, F.voice)
async def save_freedom_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение голосового для ветки Свобода"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_freedom(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Голосовое для ветки 'Свобода' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_freedom_voice)
async def wrong_freedom_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик финального призыва (голосовое)
@router.callback_query(F.data == "upload_final_voice")
async def upload_final_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку финального голосового"""
    
    prompt_text = """🏁 **Финал (Призыв)**

Запиши Голосовое сообщение для Финала.
Оно придет перед кнопкой входа в Приложение (Бизнес Хаб).

📝 **Сценарий:**
_'Короче, система полностью готова. Я уже внутри. Переходи в Бизнес Хаб, там лежат уроки и инструменты. Если что — пиши мне в личку, контакты там же. До встречи в команде!'_

⏳ **Жду голосовое...**"""
    
    try:
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_back_to_personalization(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Запись финала", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_final_voice)
    await callback.answer()

@router.message(UserStates.awaiting_final_voice, F.voice)
async def save_final_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение финального голосового"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_final(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Финальное голосовое сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_final_voice)
async def wrong_final_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "radar")
async def radar_view(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Просмотр радара активности"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Получаем события из радара
    events = await UserService.get_radar_events(session, user.id, limit=10)
    
    if not events:
        radar_text = "🕵️ **Радар Активности**\n\n"
        radar_text += "Пока нет активности от твоих лидов.\n"
        radar_text += "Поделись своей реферальной ссылкой, чтобы привлечь первых людей!"
    else:
        radar_text = "🕵️ **Радар Активности**\n\n"
        radar_text += "Здесь показаны последние действия твоих лидов:\n\n"
        
        for idx, event in enumerate(events, 1):
            # Получаем информацию о лиде
            lead = await session.get(User, event.lead_id)
            if lead:
                lead_name = lead.first_name or lead.username or "Пользователь"
                time_ago = _format_time_ago(event.created_at)
                radar_text += f"{idx}. **{lead_name}** — _{event.action_type}_ ({time_ago})\n"
    
    try:
        await callback.message.edit_text(
            radar_text,
            reply_markup=get_back_to_pro_menu(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Радар активности", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.radar_view)
    await callback.answer()

@router.callback_query(F.data.in_(["ai_mentor", "travel_architect", "calculator"]))
async def pro_tools_placeholder(callback: CallbackQuery):
    """Заглушка для инструментов PRO (реализация в части 2)"""
    
    tool_names = {
        "ai_mentor": "🤖 AI-Наставник",
        "travel_architect": "🗺 Трэвел-Архитектор",
        "calculator": "🧮 Калькулятор"
    }
    
    tool_name = tool_names.get(callback.data, "Инструмент")
    
    await callback.answer(
        f"{tool_name} будет доступен в следующем обновлении!",
        show_alert=True
    )

def _format_time_ago(created_at) -> str:
    """Форматирование времени 'назад'"""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    delta = now - created_at.replace(tzinfo=timezone.utc)
    
    minutes = int(delta.total_seconds() / 60)
    hours = int(minutes / 60)
    days = int(hours / 24)
    
    if days > 0:
        return f"{days} дн. назад"
    elif hours > 0:
        return f"{hours} ч. назад"
    elif minutes > 0:
        return f"{minutes} мин. назад"
    else:
        return "только что"

# Импорт модели User для radar_view
from bot.database.models import User