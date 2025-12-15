from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, Voice
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional
import logging
import os
import tempfile
import asyncio
from aiogram.exceptions import TelegramBadRequest

from bot.keyboards.keyboards import (
    get_ai_trainer_menu,
    get_opponent_card_keyboard,
    get_training_confirm_keyboard,
    get_training_active_keyboard,
    get_training_results_keyboard,
    get_back_to_pro_menu
)
from bot.services.user_service import UserService
from bot.services.ai_trainer_service import AITrainerService
from bot.utils.states import UserStates

router = Router()
logger = logging.getLogger(__name__)

# Эмоджи для сложности
DIFFICULTY_EMOJI = {
    'легкий': '🟢',
    'средний': '🟡',
    'сложный': '🔴',
    'эксперт': '🟣'
}

@router.callback_query(F.data == "trainer")
async def trainer_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Вход в AI-Тренажер"""
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.subscription_status != 'PRO':
        await callback.answer("⚠️ AI-Тренажер доступен только для PRO пользователей", show_alert=True)
        return
    
    welcome_text = """🥊 **AI-ТРЕНАЖЕР ВОЗРАЖЕНИЙ**

Тренируйтесь на реалистичных AI-соперниках и прокачивайте навыки работы с возражениями!

**Как это работает:**
1️⃣ Выберите соперника из библиотеки
2️⃣ AI войдет в роль клиента
3️⃣ Отвечайте на возражения голосом или текстом
4️⃣ Получите детальный анализ и рекомендации

Выберите первого соперника в библиотеке 👇🏻"""
    
    try:
        await callback.message.edit_text(
            welcome_text,
            reply_markup=get_ai_trainer_menu(),
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("AI-Тренажер", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.ai_trainer_menu)
    await callback.answer()

@router.callback_query(F.data == "trainer_menu")
async def trainer_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню тренажера"""
    await trainer_start(callback, state, callback.bot.get("session"))

@router.callback_query(F.data == "trainer_library")
async def trainer_library(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Библиотека соперников - список"""
    from bot.keyboards.keyboards import get_opponent_list_keyboard
    
    opponents = await AITrainerService.get_opponents_by_difficulty(session)
    
    if not opponents:
        try:
            await callback.message.edit_text(
                "📚 **Библиотека соперников пуста**\n\nСоперники скоро появятся!",
                reply_markup=get_back_to_pro_menu(),
                parse_mode='Markdown'
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Если сообщение не изменилось, просто отправляем ответ на callback
                await callback.answer("Библиотека пуста", show_alert=False)
            else:
                # Если другая ошибка BadRequest, пробрасываем дальше
                raise
        await callback.answer()
        return
    
    text = "📚 **БИБЛИОТЕКА СОПЕРНИКОВ**\n\n"
    text += "Выберите соперника для тренировки:\n\n"
    
    # Группируем по сложности для отображения
    grouped = {}
    for opp in opponents:
        diff = opp['difficulty']
        if diff not in grouped:
            grouped[diff] = []
        grouped[diff].append(opp)
    
    # Показываем количество по уровням
    if grouped:
        text += "📊 **Доступно:**\n"
        if 'легкий' in grouped:
            text += f"🟢 Легкий: {len(grouped['легкий'])}\n"
        if 'средний' in grouped:
            text += f"🟡 Средний: {len(grouped['средний'])}\n"
        if 'сложный' in grouped:
            text += f"🔴 Сложный: {len(grouped['сложный'])}\n"
        if 'эксперт' in grouped:
            text += f"🟣 Эксперт: {len(grouped['эксперт'])}\n"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_opponent_list_keyboard(opponents),
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Библиотека соперников", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.ai_trainer_library)
    await callback.answer()

@router.callback_query(F.data.startswith("trainer_opponent_"))
async def show_opponent_card(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать карточку соперника"""
    opponent_id = callback.data.replace("trainer_opponent_", "")
    opponent = await AITrainerService.get_opponent_by_id(session, opponent_id)
    
    if not opponent:
        await callback.answer("❌ Соперник не найден", show_alert=True)
        return
    
    card_text = format_opponent_card(opponent)
    
    try:
        await callback.message.edit_text(
            card_text,
            reply_markup=get_opponent_card_keyboard(opponent['id']),
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Карточка соперника", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await callback.answer()

def format_opponent_card(opponent: dict) -> str:
    """Форматирование карточки соперника по шаблону"""
    emoji = DIFFICULTY_EMOJI.get(opponent['difficulty'], '⭐')
    difficulty_stars = "⭐" * (4 if opponent['difficulty'] == 'сложный' else 3 if opponent['difficulty'] == 'средний' else 2)
    
    card = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    card += f"**{opponent['name']}**\n\n"
    card += f"Сложность: {difficulty_stars} ({opponent['difficulty'].capitalize()})\n\n"
    
    # Профиль
    card += "👤 **Профиль:**\n"
    age = opponent.get('age', 'N/A')
    profession = opponent.get('profession', 'N/A')
    comm_style = opponent.get('communication_style', '')
    
    card += f"{profession}, {age} лет"
    if comm_style:
        card += f",\n{comm_style}"
    card += "\n\n"
    
    # Главные возражения
    if opponent.get('core_objections'):
        objections = opponent['core_objections']
        if isinstance(objections, list) and objections:
            card += "🎯 **Главные возражения:**\n"
            for obj in objections[:3]:
                card += f"- \"{obj}\"\n"
            card += "\n"
    
    # Навыки тренировки (можно расширить позже)
    card += "💪 **Навыки тренировки:**\n"
    card += "✓ Работа с возражениями\n"
    card += "✓ Убедительная аргументация\n"
    card += "✓ Эмоциональный интеллект\n\n"
    
    # Ваши попытки
    stats = opponent.get('stats', {})
    attempts = stats.get('total_attempts', 0) if isinstance(stats, dict) else 0
    card += f"Ваши попытки: {attempts}\n\n"
    
    card += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return card

@router.callback_query(F.data.startswith("trainer_start_"))
async def trainer_start_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждение начала тренировки"""
    opponent_id = callback.data.replace("trainer_start_", "")
    opponent = await AITrainerService.get_opponent_by_id(session, opponent_id)
    
    if not opponent:
        await callback.answer("❌ Соперник не найден", show_alert=True)
        return
    
    emoji = DIFFICULTY_EMOJI.get(opponent['difficulty'], '⭐')
    
    text = f"⚠️ **ВЫ ВЫБРАЛИ:**\n\n"
    text += f"{opponent['name']}\n"
    text += f"Сложность: {emoji} {opponent['difficulty'].capitalize()}\n\n"
    text += "Готовы начать? AI войдет в роль немедленно."
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_training_confirm_keyboard(opponent_id),
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Подтверждение тренировки", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await callback.answer()

@router.callback_query(F.data.startswith("trainer_confirm_"))
async def trainer_confirm_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало тренировки"""
    opponent_id = callback.data.replace("trainer_confirm_", "")
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Проверяем, нет ли активной сессии
    active_session = await AITrainerService.get_active_session(session, str(user.id))
    if active_session:
        await callback.answer("⚠️ У вас уже есть активная тренировка", show_alert=True)
        return
    
    # Получаем данные соперника
    opponent = await AITrainerService.get_opponent_by_id(session, opponent_id)
    if not opponent:
        await callback.answer("❌ Ошибка загрузки соперника", show_alert=True)
        return
    
    # Создаем сессию тренировки
    session_id = await AITrainerService.create_training_session(
        session,
        str(user.id),
        opponent_id
    )
    
    if not session_id:
        await callback.answer("❌ Ошибка создания сессии", show_alert=True)
        return
    
    # Сохраняем ID сессии в state
    await state.update_data(training_session_id=session_id, opponent_id=opponent_id)
    await state.set_state(UserStates.ai_trainer_active)
    
    # Получаем первую реплику из промпта соперника
    first_message = extract_first_message(opponent['base_prompt'])
    
    # Уведомление о начале
    text = "🥊 **ТРЕНИРОВКА НАЧАЛАСЬ!**\n\n"
    text += f"Соперник: {opponent['name']}\n\n"
    text += "─────────────────────────────\n"
    text += "💬 Отвечайте текстом или 🎤 голосовым сообщением"
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Тренировка началась", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Сохраняем первое сообщение AI
    await AITrainerService.add_message_to_session(
        session,
        session_id,
        'assistant',
        first_message
    )
    
    # Отправляем первую реплику AI отдельным сообщением
    await callback.message.answer(
        first_message,
        reply_markup=get_training_active_keyboard(session_id)
    )
    
    await callback.answer("✅ Тренировка началась!")

def extract_first_message(prompt: str) -> str:
    """Извлечь первую реплику из промпта"""
    # Ищем секцию "ПЕРВАЯ РЕПЛИКА"
    if "# ПЕРВАЯ РЕПЛИКА" in prompt:
        parts = prompt.split("# ПЕРВАЯ РЕПЛИКА")
        if len(parts) > 1:
            lines = parts[1].strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Убираем кавычки если есть
                    return line.strip('"').strip()
    
    # Дефолтное сообщение
    return "Привет! Расскажи мне подробнее про MWR Life"

@router.message(UserStates.ai_trainer_active, F.text)
async def handle_training_text(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка текстового сообщения во время тренировки"""
    data = await state.get_data()
    session_id = data.get('training_session_id')
    opponent_id = data.get('opponent_id')
    
    if not session_id or not opponent_id:
        await message.answer("❌ Ошибка: сессия не найдена")
        return
    
    # Сохраняем сообщение пользователя
    await AITrainerService.add_message_to_session(
        session,
        session_id,
        'user',
        message.text
    )
    
    # Показываем индикатор "печатает..."
    await message.bot.send_chat_action(message.chat.id, 'typing')
    
    # Получаем данные соперника
    opponent = await AITrainerService.get_opponent_by_id(session, opponent_id)
    
    # Анализируем интент сообщения
    intent = await AITrainerService.analyze_intent(message.text)
    
    # Получаем релевантные знания из БД
    relevant_knowledge = await AITrainerService.get_relevant_knowledge(
        session,
        intent['topics']
    )
    
    # Получаем историю диалога
    conversation_history = await AITrainerService.get_session_history(session, session_id)
    
    # Генерируем ответ AI
    ai_response = await AITrainerService.generate_ai_response(
        opponent['base_prompt'],
        conversation_history,
        message.text,
        relevant_knowledge
    )
    
    if not ai_response:
        ai_response = "Хм, интересно... Расскажи подробнее?"
    
    # Сохраняем ответ AI
    await AITrainerService.add_message_to_session(
        session,
        session_id,
        'assistant',
        ai_response
    )
    
    # Отправляем ответ
    await message.answer(
        ai_response,
        reply_markup=get_training_active_keyboard(session_id)
    )

@router.message(UserStates.ai_trainer_active, F.voice)
async def handle_training_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка голосового сообщения во время тренировки"""
    data = await state.get_data()
    session_id = data.get('training_session_id')
    opponent_id = data.get('opponent_id')
    
    if not session_id or not opponent_id:
        await message.answer("❌ Ошибка: сессия не найдена")
        return
    
    await message.answer("🎤 Обрабатываю голосовое сообщение...")
    
    # Скачиваем голосовое
    voice: Voice = message.voice
    file = await message.bot.get_file(voice.file_id)
    
    # Сохраняем во временный файл
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
        await message.bot.download_file(file.file_path, temp_file)
        temp_path = temp_file.name
    
    try:
        # Транскрибируем
        transcribed_text = await AITrainerService.transcribe_voice(temp_path)
        
        if not transcribed_text:
            await message.answer("❌ Не удалось распознать голос. Попробуйте еще раз.")
            return
        
        # Сохраняем сообщение пользователя (голосовое)
        await AITrainerService.add_message_to_session(
            session,
            session_id,
            'user',
            transcribed_text,
            is_voice=True,
            voice_file_id=voice.file_id
        )
        
        # Показываем что распознали
        await message.answer(f"📝 Распознано: _{transcribed_text}_", parse_mode='Markdown')
        
        # Показываем индикатор "печатает..."
        await message.bot.send_chat_action(message.chat.id, 'typing')
        
        # Далее обрабатываем как текст
        opponent = await AITrainerService.get_opponent_by_id(session, opponent_id)
        relevant_knowledge = await AITrainerService.search_in_documents(session, transcribed_text, limit=3)
        conversation_history = await AITrainerService.get_session_history(session, session_id)
        
        ai_response = await AITrainerService.generate_ai_response(
            opponent['base_prompt'],
            conversation_history,
            transcribed_text,
            relevant_knowledge
        )
        
        if not ai_response:
            ai_response = "Хм, интересно... Расскажи подробнее?"
        
        # Сохраняем ответ AI
        await AITrainerService.add_message_to_session(
            session,
            session_id,
            'assistant',
            ai_response
        )
        
        # Отправляем ответ (только текстом, так как TTS не реализован)
        await message.answer(
            ai_response,
            reply_markup=get_training_active_keyboard(session_id)
        )
    
    finally:
        # Удаляем временный файл асинхронно
        if os.path.exists(temp_path):
            await asyncio.to_thread(os.unlink, temp_path)

@router.callback_query(F.data.startswith("trainer_end_"))
async def trainer_end_session(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Завершение тренировки с AI-анализом"""
    session_id = callback.data.replace("trainer_end_", "")
    
    # Показываем индикатор анализа
    try:
        await callback.message.edit_text(
            "⏳ **Анализирую вашу тренировку...**\n\nЭто может занять несколько секунд",
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Анализ тренировки", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await callback.answer()
    
    # Получаем данные сессии
    data = await state.get_data()
    opponent_id = data.get('opponent_id')
    
    if not opponent_id:
        try:
            await callback.message.edit_text(
                "❌ Ошибка: не удалось найти данные соперника",
                reply_markup=get_back_to_pro_menu(),
                parse_mode='Markdown'
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Если сообщение не изменилось, просто отправляем ответ на callback
                await callback.answer("Ошибка соперника", show_alert=False)
            else:
                # Если другая ошибка BadRequest, пробрасываем дальше
                raise
        return
    
    # Получаем соперника
    opponent = await AITrainerService.get_opponent_by_id(session, opponent_id)
    if not opponent:
        try:
            await callback.message.edit_text(
                "❌ Ошибка: соперник не найден",
                reply_markup=get_back_to_pro_menu(),
                parse_mode='Markdown'
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Если сообщение не изменилось, просто отправляем ответ на callback
                await callback.answer("Соперник не найден", show_alert=False)
            else:
                # Если другая ошибка BadRequest, пробрасываем дальше
                raise
        return
    
    # Получаем историю диалога
    conversation_history = await AITrainerService.get_session_history(session, session_id, limit=100)
    
    if not conversation_history or len(conversation_history) < 2:
        try:
            await callback.message.edit_text(
                "❌ Недостаточно сообщений для анализа\n\nМинимум 2 сообщения",
                reply_markup=get_back_to_pro_menu(),
                parse_mode='Markdown'
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Если сообщение не изменилось, просто отправляем ответ на callback
                await callback.answer("Недостаточно сообщений", show_alert=False)
            else:
                # Если другая ошибка BadRequest, пробрасываем дальше
                raise
        return
    
    # Запускаем AI-анализ
    analysis_result = await AITrainerService.analyze_training_session(
        conversation_history,
        opponent['name']
    )
    
    if not analysis_result:
        # Фоллбэк: базовый анализ без AI
        analysis_result = {
            'overall_score': 7.0,
            'scores': {
                'product_knowledge': 7.0,
                'objection_handling': 7.0,
                'emotional_intelligence': 7.0,
                'confidence': 7.0
            },
            'strengths': [
                'Активное участие в диалоге',
                'Попытка отработать возражения'
            ],
            'weaknesses': [
                'Недостаточно конкретики',
                'Можно больше фактов'
            ],
            'recommendations': [
                'Изучите больше деталей о продукте',
                'Практикуйте работу с конкретными возражениями',
                'Работайте над уверенностью'
            ],
            'summary': 'Хорошая попытка! Продолжайте тренироваться для улучшения навыков.'
        }
    
    # Сохраняем результаты в БД
    await AITrainerService.end_training_session(
        session,
        session_id,
        user_score=analysis_result['overall_score'],
        analysis=analysis_result.get('summary', ''),
        scores=analysis_result['scores'],
        strengths=analysis_result['strengths'],
        weaknesses=analysis_result['weaknesses'],
        recommendations=analysis_result['recommendations']
    )
    
    # Форматируем красивый результат
    text = format_training_results(
        opponent['name'],
        len(conversation_history),
        analysis_result
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_training_results_keyboard(opponent_id),
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Результаты тренировки", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    await state.clear()
    await callback.answer("✅ Анализ готов!")

def format_training_results(opponent_name: str, message_count: int, analysis: Dict) -> str:
    """Форматирование результатов тренировки"""
    scores = analysis['scores']
    
    text = "🏆 **ТРЕНИРОВКА ЗАВЕРШЕНА!**\n\n"
    text += f"**Соперник:** {opponent_name}\n"
    text += f"**Сообщений:** {message_count}\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Общая оценка
    overall = analysis['overall_score']
    stars = "⭐" * int(overall)
    text += f"**ИТОГОВАЯ ОЦЕНКА: {overall}/10** {stars}\n\n"
    
    # Детальные оценки
    text += "📊 **ДЕТАЛЬНАЯ ОЦЕНКА:**\n\n"
    text += f"🎓 Знание продукта: {scores.get('product_knowledge', 0)}/10\n"
    text += f"🛡 Работа с возражениями: {scores.get('objection_handling', 0)}/10\n"
    text += f"💝 Эмоциональный интеллект: {scores.get('emotional_intelligence', 0)}/10\n"
    text += f"💪 Уверенность: {scores.get('confidence', 0)}/10\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Сильные стороны
    if analysis.get('strengths'):
        text += "✅ **СИЛЬНЫЕ СТОРОНЫ:**\n"
        for strength in analysis['strengths'][:3]:
            text += f"• {strength}\n"
        text += "\n"
    
    # Слабые стороны
    if analysis.get('weaknesses'):
        text += "⚠️ **ЧТО УЛУЧШИТЬ:**\n"
        for weakness in analysis['weaknesses'][:3]:
            text += f"• {weakness}\n"
        text += "\n"
    
    # Рекомендации
    if analysis.get('recommendations'):
        text += "💡 **РЕКОМЕНДАЦИИ:**\n"
        for i, rec in enumerate(analysis['recommendations'][:3], 1):
            text += f"{i}. {rec}\n"
        text += "\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Итоговое резюме
    if analysis.get('summary'):
        text += f"📝 **РЕЗЮМЕ:**\n{analysis['summary']}\n\n"
    
    text += "Продолжайте тренироваться! 🚀"
    
    return text

@router.callback_query(F.data == "trainer_stats")
async def trainer_statistics(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Статистика пользователя"""
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    stats = await AITrainerService.get_user_statistics(session, str(user.id))
    
    text = "📊 **МОЯ СТАТИСТИКА**\n\n"
    text += f"🥊 Всего тренировок: {stats['total_sessions']}\n"
    text += f"⭐ Средний балл: {stats['average_score']}/10\n\n"
    
    if stats['recent_sessions']:
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "📝 **ПОСЛЕДНИЕ ТРЕНИРОВКИ:**\n\n"
        for s in stats['recent_sessions'][:5]:
            opponent_name = s.get('opponent_name', 'Неизвестный')
            score = s.get('user_score', 0)
            messages = s.get('message_count', 0)
            stars = "⭐" * int(score) if score > 0 else "—"
            text += f"**{opponent_name}**\n"
            text += f"Оценка: {score}/10 {stars}\n"
            text += f"Сообщений: {messages}\n\n"
    else:
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += "У вас пока нет завершенных тренировок.\n\n"
        text += "💡 Начните первую тренировку!\n"
        text += "Выберите соперника из библиотеки 👇🏻"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_ai_trainer_menu(),
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Статистика", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await callback.answer()