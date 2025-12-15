"""
Хендлер для модуля Контент-Мейкер
Обрабатывает создание персонализированного контента для социальных сетей
"""

import logging
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.states import ContentMakerStates
from bot.keyboards.keyboards import (
    get_content_maker_main_menu,
    get_content_maker_profile_choice,
    get_content_maker_profile_view,
    get_back_to_content_maker
)
from bot.services.content_profile_service import ContentProfileService
from bot.services.user_service import UserService

logger = logging.getLogger(__name__)

router = Router()

# Кэшируем путь к PDF и file_id для ускорения отправки
_PDF_PATH = Path.cwd() / "Контент-Мейкер. Гайд.pdf"  # Ищем PDF в корневой директории
_PDF_FILE_ID = None  # Будет заполнен после первой отправки


# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

async def cleanup_messages(bot, chat_id: int, message_ids: list):
    """
    Удалить список сообщений из чата
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        message_ids: Список ID сообщений для удаления
    """
    if not message_ids:
        return
    
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")


async def safe_edit_or_send(message: Message, text: str, **kwargs):
    """
    Безопасно редактирует или отправляет новое сообщение.
    Используется для избежания ошибки "there is no text in the message to edit"
    когда callback.message содержит документ вместо текста.
    
    Args:
        message: Объект сообщения
        text: Текст для отправки
        **kwargs: Дополнительные параметры (reply_markup, parse_mode, и т.д.)
    
    Returns:
        Message: Отредактированное или новое сообщение
    """
    try:
        # Проверяем, можно ли отредактировать сообщение
        # Если у сообщения есть text, пробуем отредактировать
        if message.text:
            return await message.edit_text(text, **kwargs)
        else:
            # Если у сообщения нет text (например, это документ), удаляем и отправляем новое
            try:
                await message.delete()
            except Exception as e:
                logger.debug(f"Не удалось удалить сообщение: {e}")
            
            return await message.answer(text, **kwargs)
    except Exception as e:
        # Если не удалось отредактировать, отправляем новое
        logger.debug(f"Не удалось отредактировать сообщение, отправляем новое: {e}")
        return await message.answer(text, **kwargs)


# ============ ГЛАВНОЕ МЕНЮ И ВХОД ============

@router.callback_query(F.data == "content_maker")
async def content_maker_entry(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Точка входа в модуль Контент-Мейкер
    Проверяет наличие профиля и показывает соответствующее меню
    """
    try:
        await callback.answer()
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        
        if not user:
            await callback.message.edit_text("❌ Ошибка: пользователь не найден")
            return
        
        # Всегда показываем главное меню по требованию пользователя
        await show_main_menu(callback.message, state)
            
    except Exception as e:
        logger.error(f"Ошибка при входе в контент-мейкер: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_to_content_maker()
        )


async def show_welcome_message(message: Message, state: FSMContext):
    """Показать приветственное сообщение для нового пользователя"""
    
    welcome_text = """👋 *Привет! Это твой личный Контент-Мейкер.*

Я помогу тебе вести соцсети так, чтобы люди сами интересовались твоим стилем жизни и бизнесом. Без выгорания и творческих мук.

Гайд по работе с ботом будет доступен в главном меню.

---

Чтобы начать, мне нужно узнать твой стиль.
Давай заполним твой профиль автора. Это один раз.

*Как тебе удобнее?*"""
    
    await message.edit_text(
        welcome_text,
        reply_markup=get_content_maker_profile_choice(),
        parse_mode="Markdown"
    )
    # PDF гайд больше не отправляется здесь, он будет в главном меню
    await state.set_state(ContentMakerStates.profile_fill_choice)


async def show_main_menu(message: Message, state: FSMContext):
    """Показать главное меню контент-мейкера в виде одного сообщения с PDF"""
    global _PDF_FILE_ID
    
    # Очищаем предыдущие сообщения, если они были
    data = await state.get_data()
    old_messages = data.get('cm_messages_to_delete', [])
    if old_messages:
        await cleanup_messages(message.bot, message.chat.id, old_messages)
        await state.update_data(cm_messages_to_delete=[])

    # Удаляем сообщение, с которого был выполнен переход (например, главное меню)
    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"Не удалось удалить исходное сообщение: {e}")

    menu_text = """✍️ *КОНТЕНТ-МЕЙКЕР*

Гайд по работе с ботом прикреплен к этому сообщению.

Выбери действие:"""
    
    # Отправляем одно сообщение: PDF + Текст (caption) + Кнопки
    try:
        # Используем кешированный file_id если есть
        if _PDF_FILE_ID:
            try:
                sent = await message.answer_document(
                    document=_PDF_FILE_ID,
                    caption=menu_text,
                    reply_markup=get_content_maker_main_menu(),
                    parse_mode="Markdown"
                )
            except Exception as e:
                # Если file_id устарел, отправляем файл заново
                logger.debug(f"Кешированный file_id не работает, загружаем файл: {e}")
                _PDF_FILE_ID = None  # Сбрасываем кеш
                # Повторяем отправку с файлом
                if _PDF_PATH.exists():
                    pdf_file = FSInputFile(_PDF_PATH)
                    sent = await message.answer_document(
                        document=pdf_file,
                        caption=menu_text,
                        reply_markup=get_content_maker_main_menu(),
                        parse_mode="Markdown"
                    )
                    # Сохраняем file_id для будущих использований
                    if sent.document:
                        _PDF_FILE_ID = sent.document.file_id
                else:
                    # PDF не найден
                    await message.answer(
                        menu_text,
                        reply_markup=get_content_maker_main_menu(),
                        parse_mode="Markdown"
                    )
        elif _PDF_PATH.exists():
            # Первая загрузка PDF
            pdf_file = FSInputFile(_PDF_PATH)
            sent = await message.answer_document(
                document=pdf_file,
                caption=menu_text,
                reply_markup=get_content_maker_main_menu(),
                parse_mode="Markdown"
            )
            # Сохраняем file_id для будущих использований
            if sent.document:
                _PDF_FILE_ID = sent.document.file_id
                logger.debug(f"PDF file_id закеширован: {_PDF_FILE_ID}")
        else:
            # Если PDF не найден, отправляем просто текст с кнопками
            logger.warning(f"PDF файл не найден по пути: {_PDF_PATH}")
            await message.answer(
                menu_text,
                reply_markup=get_content_maker_main_menu(),
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Не удалось отправить главное меню контент-мейкера: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_to_content_maker()
        )
    
    await state.set_state(ContentMakerStates.profile_view)


@router.callback_query(F.data == "cm_main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню контент-мейкера"""
    try:
        await callback.answer()
        await show_main_menu(callback.message, state)
    except Exception as e:
        logger.error(f"Ошибка при возврате в главное меню: {e}", exc_info=True)


# ============ НАСТРОЙКИ ПЕРСОНАЛИЗАЦИИ ============

@router.callback_query(F.data == "cm_personalization")
async def show_personalization_settings(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать настройки персонализации (просмотр/редактирование профиля)"""
    try:
        await callback.answer()
        
        # Удаляем сообщение "Полный Профиль", если оно есть
        data = await state.get_data()
        full_profile_msg_id = data.get('full_profile_msg_id')
        if full_profile_msg_id:
            try:
                await callback.bot.delete_message(callback.message.chat.id, full_profile_msg_id)
                await state.update_data(full_profile_msg_id=None)
            except Exception as e:
                logger.debug(f"Не удалось удалить сообщение полного профиля: {e}")
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        
        if not user:
            try:
                await callback.message.edit_text("❌ Ошибка: пользователь не найден")
            except Exception:
                await callback.message.answer("❌ Ошибка: пользователь не найден")
            return
        
        # Получаем профиль
        profile_data = await ContentProfileService.get_profile_data(session, user.id)
        
        if not profile_data:
            try:
                await callback.message.edit_text(
                    "❓ Профиль не найден. Пожалуйста, заполните его сначала.",
                    reply_markup=get_content_maker_profile_choice()
                )
            except Exception:
                await callback.message.answer(
                    "❓ Профиль не найден. Пожалуйста, заполните его сначала.",
                    reply_markup=get_content_maker_profile_choice()
                )
            await state.set_state(ContentMakerStates.profile_fill_choice)
            return
        
        # Формируем краткое описание профиля
        who = profile_data.get('who_are_you', {})
        travel = profile_data.get('travel_experience', {})
        character = profile_data.get('character', {})
        goals = profile_data.get('goals', {})
        
        profile_summary = f"""⚙️ *НАСТРОЙКИ ПЕРСОНАЛИЗАЦИИ*

Твой профиль уже заполнен.

*Кратко:*
• Имя: {who.get('name', 'не указано')}, {who.get('age', '?')} лет, {who.get('city', 'не указан')}
• Род занятий: {who.get('occupation', 'не указано')}
• Стиль общения: {character.get('communication_style', 'не указан')}
• Travel-опыт: {travel.get('level', 'не указан')}, {travel.get('countries_count', '?')} стран
• Основные цели: {', '.join(goals.get('main_goals', ['не указаны'])[:2])}

Что хочешь сделать?"""
        
        try:
            await callback.message.edit_text(
                profile_summary,
                reply_markup=get_content_maker_profile_view(),
                parse_mode="Markdown"
            )
        except Exception as e:
            # Если не удалось отредактировать (например, сообщение удалено), отправляем новое
            logger.debug(f"Не удалось отредактировать сообщение, отправляем новое: {e}")
            await callback.message.answer(
                profile_summary,
                reply_markup=get_content_maker_profile_view(),
                parse_mode="Markdown"
            )
        
        await state.set_state(ContentMakerStates.profile_view)
        
    except Exception as e:
        logger.error(f"Ошибка при отображении настроек персонализации: {e}", exc_info=True)
        try:
            await callback.message.edit_text(
                "❌ Произошла ошибка при загрузке профиля.",
                reply_markup=get_back_to_content_maker()
            )
        except Exception:
            await callback.message.answer(
                "❌ Произошла ошибка при загрузке профиля.",
                reply_markup=get_back_to_content_maker()
            )


@router.callback_query(F.data == "cm_profile_view_full")
async def view_full_profile(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать полный профиль пользователя"""
    try:
        await callback.answer()
        
        # Удаляем предыдущий полный профиль, если он был
        data = await state.get_data()
        old_full_profile_msg_id = data.get('full_profile_msg_id')
        if old_full_profile_msg_id:
            try:
                await callback.bot.delete_message(callback.message.chat.id, old_full_profile_msg_id)
            except Exception as e:
                logger.debug(f"Не удалось удалить предыдущее сообщение профиля: {e}")
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        
        if not user:
            await callback.message.answer("❌ Ошибка: пользователь не найден")
            return
        
        profile_data = await ContentProfileService.get_profile_data(session, user.id)
        
        if not profile_data:
            await callback.message.answer("❓ Профиль не найден")
            return
        
        # Формируем полное описание
        who = profile_data.get('who_are_you', {})
        travel = profile_data.get('travel_experience', {})
        character = profile_data.get('character', {})
        goals = profile_data.get('goals', {})
        
        full_profile = f"""👤 *ПОЛНЫЙ ПРОФИЛЬ*

*КТО ТЫ:*
• Имя: {who.get('name', 'не указано')}
• Возраст: {who.get('age', 'не указан')}
• Город: {who.get('city', 'не указан')}
• Род занятий: {who.get('occupation', 'не указано')}
• Экспертиза: {who.get('expertise', 'не указана')}

*TRAVEL ОПЫТ:*
• Уровень: {travel.get('level', 'не указан')}
• Страны: {travel.get('countries_count', 'не указано')}
• Стиль: {travel.get('style', 'не указан')}
• Мечта: {travel.get('dream_destination', 'не указана')}

*ХАРАКТЕР:*
• Стиль общения: {character.get('communication_style', 'не указан')}
• Интересы: {', '.join(character.get('topics_of_interest', ['не указаны']))}
• Раздражает: {', '.join(character.get('pet_peeves', ['не указано']))}

*ЦЕЛИ:*
• Основные: {', '.join(goals.get('main_goals', ['не указаны']))}
• Страсть сейчас: {goals.get('current_passion', 'не указана')}"""
        
        from bot.keyboards.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="cm_personalization")]
        ])
        
        # Отправляем новое сообщение и сохраняем его ID
        sent_msg = await callback.message.answer(
            full_profile,
            reply_markup=back_keyboard,
            parse_mode="Markdown"
        )
        
        await state.update_data(full_profile_msg_id=sent_msg.message_id)
        
    except Exception as e:
        logger.error(f"Ошибка при отображении полного профиля: {e}", exc_info=True)
        await callback.message.answer("❌ Произошла ошибка при загрузке профиля")


@router.callback_query(F.data == "cm_profile_rewrite")
async def rewrite_profile_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение перезаписи профиля"""
    try:
        await callback.answer()
        
        confirm_text = """⚠️ *ВНИМАНИЕ!*

Ты уверен, что хочешь перезаписать профиль?

Текущие данные будут заменены новыми.

*Как заполнить новый профиль?*"""
        
        await safe_edit_or_send(
            callback.message,
            confirm_text,
            reply_markup=get_content_maker_profile_choice(show_back=True),
            parse_mode="Markdown"
        )
        
        await state.set_state(ContentMakerStates.profile_fill_choice)
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении перезаписи профиля: {e}", exc_info=True)
        await callback.message.answer("❌ Произошла ошибка. Попробуйте позже.")


# ============ ЗАПОЛНЕНИЕ ПРОФИЛЯ ТЕКСТОМ ============

@router.callback_query(F.data == "cm_profile_text")
async def profile_fill_text_start(callback: CallbackQuery, state: FSMContext):
    """Начало заполнения профиля текстом"""
    try:
        await callback.answer()
        
        template_text = """📝 *Заполняем профиль текстом*

Скопируй шаблон ниже, заполни его (можно своими словами) и отправь мне ответным сообщением.

👇 *Нажми, чтобы скопировать:*

`1️⃣ КТО ТЫ?
Имя, возраст, город. Чем занимаешься (работа, бизнес, фриланс)? В чём ты реально разбираешься?

2️⃣ ПУТЕШЕСТВИЯ & ОПЫТ
Ты новичок или бывалый? (Сколько стран?). Какой стиль любишь (эконом/лакшери, соло/семья)? О какой поездке мечтаешь?

3️⃣ ТВОЙ ВАЙБ (ХАРАКТЕР)
Как ты общаешься? (Дерзко, по-дружески, официально, с юмором). О чём любишь поговорить? Что тебя бесит в людях или мире?

4️⃣ ТВОИ ЦЕЛИ
К чему идёшь? Чем горишь прямо сейчас? (Свобода, деньги, популярность, помощь людям, увидеть весь мир...).`

---

Не обязательно отвечать сухо по пунктам — говори своими словами, как в жизни. Чем живее расскажешь, тем круче я буду писать."""
        
        from bot.keyboards.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="content_maker")]
        ])
        
        await safe_edit_or_send(
            callback.message,
            template_text,
            reply_markup=back_keyboard,
            parse_mode="Markdown"
        )
        
        await state.set_state(ContentMakerStates.profile_fill_text)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске заполнения профиля текстом: {e}", exc_info=True)
        await callback.message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.message(ContentMakerStates.profile_fill_text)
async def profile_fill_text_process(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка текста профиля от пользователя"""
    try:
        user_text = message.text
        
        if not user_text or len(user_text) < 50:
            await message.answer(
                "❌ Слишком короткий текст. Пожалуйста, расскажи подробнее о себе (минимум 50 символов)."
            )
            return
        
        # Показываем индикатор обработки
        processing_msg = await message.answer("⏳ Обрабатываю твой профиль...")
        
        user = await UserService.get_user_by_telegram_id(session, str(message.from_user.id))
        
        if not user:
            await processing_msg.edit_text("❌ Ошибка: пользователь не найден")
            return
        
        # Парсим профиль через LLM
        from bot.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        
        profile_data = await llm_service.parse_profile_from_text(user_text)
        
        # Сохраняем профиль
        await ContentProfileService.create_or_update_profile(
            session,
            user.id,
            profile_data
        )
        
        await processing_msg.delete()
        
        await message.answer(
            "✅ *Профиль сохранён!*\n\nТеперь я знаю твой стиль и буду генерировать персонализированный контент.",
            parse_mode="Markdown"
        )
        
        # Показываем главное меню
        menu_msg = await message.answer("Загружаю меню...")
        await show_main_menu(menu_msg, state)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке текста профиля: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке профиля. Попробуйте ещё раз.",
            reply_markup=get_back_to_content_maker()
        )


# ============ ЗАПОЛНЕНИЕ ПРОФИЛЯ ГОЛОСОМ ============

@router.callback_query(F.data == "cm_profile_voice")
async def profile_fill_voice_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало заполнения профиля голосом"""
    try:
        await callback.answer()
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        
        if not user:
            await callback.message.answer("❌ Ошибка: пользователь не найден")
            return
        
        # Создаем новую голосовую сессию
        voice_session = await ContentProfileService.create_voice_session(session, user.id)
        
        # Сохраняем ID сессии в state
        await state.update_data(voice_session_id=str(voice_session.id))
        
        template_text = """🎙 *Заполняем профиль голосом*

Это самый простой способ. Просто расскажи мне о себе, как другу.

👇 *Используй эту шпаргалку как опору.*
Не обязательно отвечать сухо по пунктам — говори своими словами, как в жизни. Чем живее расскажешь, тем круче я буду писать.

`1️⃣ КТО ТЫ?
Имя, возраст, город. Чем занимаешься (работа, бизнес, фриланс)? В чём ты реально разбираешься?

2️⃣ ПУТЕШЕСТВИЯ & ОПЫТ
Ты новичок или бывалый? (Сколько стран?). Какой стиль любишь (эконом/лакшери, соло/семья)? О какой поездке мечтаешь?

3️⃣ ТВОЙ ВАЙБ (ХАРАКТЕР)
Как ты общаешься? (Дерзко, по-дружески, официально, с юмором). О чём любишь поговорить? Что тебя бесит в людях или мире?

4️⃣ ТВОИ ЦЕЛИ
К чему идёшь? Чем горишь прямо сейчас? (Свобода, деньги, популярность, помощь людям, увидеть весь мир...).`

---

🎤 *Нажми на микрофон и начинай говорить.*
Я буду ждать, пока ты не нажмёшь кнопку "Завершить"."""
        
        from bot.keyboards.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="content_maker")]
        ])
        
        await safe_edit_or_send(
            callback.message,
            template_text,
            reply_markup=back_keyboard,
            parse_mode="Markdown"
        )
        
        await state.set_state(ContentMakerStates.profile_fill_voice)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске голосового заполнения: {e}", exc_info=True)
        await callback.message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_to_content_maker()
        )


@router.message(ContentMakerStates.profile_fill_voice, F.voice)
async def profile_fill_voice_receive(message: Message, state: FSMContext, session: AsyncSession):
    """Получение голосового сообщения для профиля"""
    try:
        user = await UserService.get_user_by_telegram_id(session, str(message.from_user.id))
        
        if not user:
            await message.answer("❌ Ошибка: пользователь не найден")
            return
        
        # Получаем ID сессии из state
        data = await state.get_data()
        session_id = data.get('voice_session_id')
        
        if not session_id:
            await message.answer("❌ Сессия не найдена. Начните заново.")
            return
        
        # Сохраняем голосовой фрагмент
        from uuid import UUID
        await ContentProfileService.add_voice_chunk(
            session,
            UUID(session_id),
            message.voice.file_id,
            message.voice.duration
        )
        
        # Показываем кнопки управления сессией
        from bot.keyboards.keyboards import get_content_maker_voice_session
        
        await message.answer(
            f"✅ Часть {data.get('voice_count', 0) + 1} получена.\n\nПродолжай или завершай запись:",
            reply_markup=get_content_maker_voice_session()
        )
        
        # Обновляем счётчик
        await state.update_data(voice_count=data.get('voice_count', 0) + 1)
        
    except Exception as e:
        logger.error(f"Ошибка при получении голосового сообщения: {e}", exc_info=True)
        await message.answer("❌ Ошибка при сохранении голосового сообщения")


@router.callback_query(F.data == "cm_voice_continue", ContentMakerStates.profile_fill_voice)
async def voice_continue(callback: CallbackQuery):
    """Продолжить запись голоса"""
    try:
        await callback.answer("Продолжайте запись 🎤")
    except Exception as e:
        logger.error(f"Ошибка при продолжении записи: {e}", exc_info=True)


@router.callback_query(F.data == "cm_voice_finish", ContentMakerStates.profile_fill_voice)
async def voice_finish(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Завершить голосовую сессию и обработать"""
    try:
        await callback.answer()
        
        processing_msg = await callback.message.edit_text("⏳ Обрабатываю голосовые сообщения...")
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        
        if not user:
            await processing_msg.edit_text("❌ Ошибка: пользователь не найден")
            return
        
        # Получаем ID сессии
        data = await state.get_data()
        session_id = data.get('voice_session_id')
        
        if not session_id:
            await processing_msg.edit_text("❌ Сессия не найдена")
            return
        
        from uuid import UUID
        session_uuid = UUID(session_id)
        
        # Получаем все голосовые фрагменты
        chunks = await ContentProfileService.get_session_voice_chunks(session, session_uuid)
        
        if not chunks:
            await processing_msg.edit_text("❌ Голосовые сообщения не найдены")
            return
        
        # Транскрибируем все фрагменты
        from bot.services.whisper_service import get_whisper_service
        from aiogram import Bot
        
        whisper_service = get_whisper_service()
        bot = callback.bot
        
        file_ids = [chunk.file_id for chunk in chunks]
        
        await processing_msg.edit_text(f"🎙 Транскрибирую {len(file_ids)} голосовых сообщений...")
        
        combined_transcript = await whisper_service.transcribe_multiple_voices(bot, file_ids)
        
        # Парсим профиль через LLM
        await processing_msg.edit_text("🤖 Анализирую твой профиль...")
        
        from bot.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        
        profile_data = await llm_service.parse_profile_from_text(combined_transcript)
        
        # Сохраняем профиль
        await ContentProfileService.create_or_update_profile(
            session,
            user.id,
            profile_data
        )
        
        # Закрываем сессию
        await ContentProfileService.close_voice_session(session, session_uuid)
        
        await processing_msg.edit_text(
            "✅ *Профиль сохранён!*\n\nТеперь я знаю твой стиль и буду генерировать персонализированный контент.",
            parse_mode="Markdown"
        )
        
        # Показываем главное меню
        menu_msg = await callback.message.answer("Загружаю меню...")
        await show_main_menu(menu_msg, state)
        
        # Очищаем state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при завершении голосовой сессии: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Произошла ошибка при обработке голоса. Попробуйте заново.",
            reply_markup=get_back_to_content_maker()
        )


# ============ ГЕНЕРАЦИЯ ИДЕЙ ============

@router.callback_query(F.data == "cm_generate_ideas")
async def generate_ideas_start(callback: CallbackQuery, state: FSMContext):
    """Начало генерации идей - выбор типа контента"""
    try:
        await callback.answer()
        
        from bot.keyboards.keyboards import get_content_types_keyboard
        
        await safe_edit_or_send(
            callback.message,
            "*💡 ГЕНЕРАЦИЯ ИДЕЙ*\n\nВыбери тип контента:",
            reply_markup=get_content_types_keyboard(),
            parse_mode="Markdown"
        )
        
        await state.set_state(ContentMakerStates.idea_select_type)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске генерации идей: {e}", exc_info=True)
        await callback.message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("cm_type_"), ContentMakerStates.idea_select_type)
async def select_content_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа контента"""
    try:
        await callback.answer()
        
        # Извлекаем ID типа контента
        type_id = int(callback.data.split("_")[-1])
        
        # Сохраняем в state
        await state.update_data(selected_content_type=type_id)
        
        from bot.keyboards.keyboards import get_platform_keyboard
        
        await callback.message.edit_text(
            "*Выбери платформу:*",
            reply_markup=get_platform_keyboard(),
            parse_mode="Markdown"
        )
        
        await state.set_state(ContentMakerStates.idea_select_platform)
        
    except Exception as e:
        logger.error(f"Ошибка при выборе типа контента: {e}", exc_info=True)


@router.callback_query(F.data.startswith("cm_platform_"), ContentMakerStates.idea_select_platform)
async def select_platform_and_generate(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор платформы и генерация идей"""
    try:
        await callback.answer()
        
        # Извлекаем платформу
        platform = callback.data.split("_")[-1]
        
        processing_msg = await callback.message.edit_text("⏳ Генерирую идеи...")
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        if not user:
            await processing_msg.edit_text("❌ Пользователь не найден")
            return
        
        # Получаем данные из state
        data = await state.get_data()
        type_id = data.get('selected_content_type')
        
        # Получаем профиль и тип контента
        profile_data = await ContentProfileService.get_profile_data(session, user.id)
        
        from bot.services.content_ideas_service import ContentIdeasService
        content_type = await ContentIdeasService.get_content_type_by_id(session, type_id)
        
        if not content_type:
            await processing_msg.edit_text("❌ Тип контента не найден")
            return
        
        # Генерируем идеи через LLM
        from bot.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        
        ideas = await llm_service.generate_content_ideas(
            profile_data,
            content_type.name,
            content_type.description or "",
            platform
        )
        
        # Очищаем предыдущие сообщения
        data = await state.get_data()
        old_messages = data.get('cm_messages_to_delete', [])
        if old_messages:
            await cleanup_messages(callback.bot, callback.message.chat.id, old_messages)
        
        # Сохраняем идеи в state
        await state.update_data(
            generated_ideas=ideas,
            selected_platform=platform,
            selected_content_type_name=content_type.name,
            current_idea_index=0,
            cm_messages_to_delete=[]
        )
        
        # Показываем первую идею
        await show_idea_at_index(processing_msg, state, 0, ideas)
        
        await state.set_state(ContentMakerStates.idea_generated)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации идей: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Ошибка при генерации идей",
            reply_markup=get_back_to_content_maker()
        )


@router.callback_query(F.data.startswith("cm_save_idea_"))
async def save_idea_to_planner(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Сохранить идею в планер"""
    try:
        idea_index = int(callback.data.split("_")[-1])
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        data = await state.get_data()
        ideas = data.get('generated_ideas', [])
        
        if idea_index >= len(ideas):
            await callback.answer("❌ Идея не найдена", show_alert=True)
            return
        
        idea = ideas[idea_index]
        
        # Сохраняем в БД
        from bot.services.content_ideas_service import ContentIdeasService
        
        await ContentIdeasService.create_idea(
            session,
            user.id,
            title=idea['title'],
            description=idea['description'],
            content_type_id=data.get('selected_content_type'),
            platform=data.get('selected_platform'),
            is_saved=True
        )
        
        await callback.answer("✅ Идея сохранена в планер", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении идеи: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при сохранении", show_alert=True)


async def show_idea_at_index(message: Message, state: FSMContext, index: int, ideas: list):
    """Показать идею по индексу"""
    try:
        if index < 0 or index >= len(ideas):
            return
        
        idea = ideas[index]
        
        idea_text = f"*💡 ИДЕЯ #{index + 1}*\n\n"
        idea_text += f"*{idea['title']}*\n\n"
        idea_text += f"{idea['description']}"
        
        from bot.keyboards.keyboards import get_idea_navigation_keyboard
        
        await message.edit_text(
            idea_text,
            reply_markup=get_idea_navigation_keyboard(index, len(ideas)),
            parse_mode="Markdown"
        )
        
        # Обновляем текущий индекс в state
        await state.update_data(current_idea_index=index)
        
    except Exception as e:
        logger.error(f"Ошибка при отображении идеи: {e}", exc_info=True)


@router.callback_query(F.data.startswith("cm_idea_nav_"))
async def navigate_ideas(callback: CallbackQuery, state: FSMContext):
    """Навигация по идеям"""
    try:
        await callback.answer()
        
        new_index = int(callback.data.split("_")[-1])
        
        data = await state.get_data()
        ideas = data.get('generated_ideas', [])
        
        if not ideas:
            await callback.message.edit_text("❌ Идеи не найдены")
            return
        
        await show_idea_at_index(callback.message, state, new_index, ideas)
        
    except Exception as e:
        logger.error(f"Ошибка при навигации по идеям: {e}", exc_info=True)


@router.callback_query(F.data == "cm_idea_position")
async def idea_position_click(callback: CallbackQuery):
    """Обработка нажатия на кнопку позиции (ничего не делает)"""
    await callback.answer()


@router.callback_query(F.data.startswith("cm_select_idea_"))
async def select_idea_for_post(callback: CallbackQuery, state: FSMContext):
    """Выбрать идею для написания поста"""
    try:
        await callback.answer()
        
        idea_index = int(callback.data.split("_")[-1])
        
        data = await state.get_data()
        ideas = data.get('generated_ideas', [])
        
        if idea_index >= len(ideas):
            await callback.message.answer("❌ Идея не найдена")
            return
        
        # Сохраняем выбранную идею
        await state.update_data(selected_idea_index=idea_index)
        
        # Переходим к генерации поста
        await generate_post_from_idea(callback, state, callback.bot)
        
    except Exception as e:
        logger.error(f"Ошибка при выборе идеи: {e}", exc_info=True)


# ============ НАПИСАНИЕ ПОСТОВ ============

@router.callback_query(F.data == "cm_write_custom_post")
async def write_custom_post_start(callback: CallbackQuery, state: FSMContext):
    """Написание поста на свою тему - сразу запрашиваем идею"""
    try:
        await callback.answer()
        
        from bot.keyboards.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="cm_main")]
        ])
        
        await safe_edit_or_send(
            callback.message,
            "*📝 НАПИСАТЬ НА СВОЮ ТЕМУ*\n\nОпиши свою идею для поста текстом:",
            reply_markup=back_keyboard,
            parse_mode="Markdown"
        )
        
        await state.set_state(ContentMakerStates.post_custom_idea)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске написания поста: {e}", exc_info=True)
        await callback.message.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data == "cm_write_from_planner")
async def write_from_planner_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало написания поста из планера"""
    try:
        await callback.answer()
        
        # Показываем планер для выбора идеи
        await show_planner(callback, state, session)
        
    except Exception as e:
        logger.error(f"Ошибка при открытии планера для поста: {e}", exc_info=True)


async def generate_post_from_idea(callback: CallbackQuery, state: FSMContext, bot):
    """Генерация поста из выбранной идеи"""
    try:
        processing_msg = await callback.message.answer("⏳ Пишу пост...")
        
        from aiogram.client.session.aiohttp import AiohttpSession
        session_maker = bot.session_pool if hasattr(bot, 'session_pool') else None
        
        # Получаем сессию БД через middleware (упрощенная версия)
        from bot.database.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
            
            if not user:
                await processing_msg.edit_text("❌ Пользователь не найден")
                return
            
            data = await state.get_data()
            ideas = data.get('generated_ideas', [])
            idea_index = data.get('selected_idea_index', 0)
            
            if idea_index >= len(ideas):
                await processing_msg.edit_text("❌ Идея не найдена")
                return
            
            idea = ideas[idea_index]
            
            # Получаем профиль
            profile_data = await ContentProfileService.get_profile_data(session, user.id)
            
            # Генерируем пост
            from bot.services.llm_service import get_llm_service
            llm_service = get_llm_service()
            
            post_text = await llm_service.generate_post(
                profile_data,
                idea['title'],
                idea['description'],
                data.get('selected_content_type_name', 'Контент'),
                data.get('selected_platform', 'telegram')
            )
            
            # Сохраняем пост в БД
            from bot.services.content_posts_service import ContentPostsService
            
            post = await ContentPostsService.create_post(
                session,
                user.id,
                platform=data.get('selected_platform', 'telegram'),
                body=post_text,
                version=1,
                status='draft'
            )
            
            await session.commit()
            
            # Очищаем предыдущие сообщения
            old_messages = data.get('cm_messages_to_delete', [])
            if old_messages:
                await cleanup_messages(bot, callback.message.chat.id, old_messages)
            
            # Показываем пост
            from bot.keyboards.keyboards import get_post_actions_keyboard
            
            await processing_msg.edit_text(
                f"{post_text}\n\n---\n_Вариант 1 (основной)_",
                reply_markup=get_post_actions_keyboard(str(post.id)),
                parse_mode="Markdown"
            )
            
            await state.update_data(
                current_post_id=str(post.id),
                cm_messages_to_delete=[]
            )
            await state.set_state(ContentMakerStates.post_viewing)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации поста: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка при генерации поста")


@router.callback_query(F.data.startswith("cm_copy_post_"))
async def copy_post(callback: CallbackQuery):
    """Скопировать пост"""
    try:
        post_id = callback.data.replace("cm_copy_post_", "")
        
        from bot.database.database import AsyncSessionLocal
        from uuid import UUID
        
        async with AsyncSessionLocal() as session:
            from bot.services.content_posts_service import ContentPostsService
            
            post = await ContentPostsService.get_post(session, UUID(post_id))
            
            if post:
                # Отправляем текст поста с кнопкой "Назад"
                await callback.message.answer(
                    f"📋 *Твой пост:*\n\n```\n{post.body}\n```\n\n_Нажми на текст выше, чтобы скопировать_",
                    parse_mode="Markdown",
                    reply_markup=get_back_to_content_maker()
                )
                await callback.answer("✅ Пост готов к копированию")
            else:
                await callback.answer("❌ Пост не найден", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при копировании поста: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("cm_edit_post_"))
async def edit_post_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование поста"""
    try:
        await callback.answer()
        
        post_id = callback.data.replace("cm_edit_post_", "")
        
        # Сохраняем ID поста в state
        await state.update_data(editing_post_id=post_id)
        
        await callback.message.answer(
            "✏️ *РЕДАКТИРОВАНИЕ ПОСТА*\n\nНапиши, что нужно изменить в посте, или отправь полностью новый текст.",
            parse_mode="Markdown"
        )
        
        await state.set_state(ContentMakerStates.post_editing)
        
    except Exception as e:
        logger.error(f"Ошибка при начале редактирования поста: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(ContentMakerStates.post_editing, F.voice)
async def edit_post_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Редактирование поста голосовым сообщением"""
    try:
        # Транскрибируем голосовое
        from bot.services.whisper_service import get_whisper_service
        whisper_service = get_whisper_service()
        
        processing_msg = await message.answer("⏳ Обрабатываю голосовое...")
        
        transcript = await whisper_service.transcribe_voice(message.bot, message.voice.file_id)
        
        if not transcript or len(transcript) < 10:
            await processing_msg.edit_text("❌ Не удалось распознать текст. Попробуйте ещё раз.")
            return
        
        # Обрабатываем как текстовую инструкцию
        await processing_msg.delete()
        await edit_post_with_llm(message, state, session, transcript)
        
    except Exception as e:
        logger.error(f"Ошибка при голосовом редактировании: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обработке голосового сообщения")


@router.message(ContentMakerStates.post_editing, F.text)
async def edit_post_text(message: Message, state: FSMContext, session: AsyncSession):
    """Редактирование поста текстовой инструкцией"""
    try:
        instruction = message.text
        
        if not instruction or len(instruction) < 5:
            await message.answer("❌ Инструкция слишком короткая. Попробуйте ещё раз.")
            return
        
        await edit_post_with_llm(message, state, session, instruction)
        
    except Exception as e:
        logger.error(f"Ошибка при текстовом редактировании: {e}", exc_info=True)
        await message.answer("❌ Ошибка при редактировании поста")


async def edit_post_with_llm(message: Message, state: FSMContext, session: AsyncSession, instruction: str):
    """Редактирование поста через LLM"""
    try:
        data = await state.get_data()
        post_id = data.get('editing_post_id')
        
        if not post_id:
            await message.answer("❌ Ошибка: пост не найден")
            return
        
        processing_msg = await message.answer("⏳ Обрабатываю правки...")
        
        from bot.services.content_posts_service import ContentPostsService
        from uuid import UUID
        
        # Получаем текущий пост
        post = await ContentPostsService.get_post(session, UUID(post_id))
        
        if not post:
            await processing_msg.edit_text("❌ Пост не найден")
            return
        
        # Получаем профиль для персонализации
        user = await UserService.get_user_by_telegram_id(session, str(message.from_user.id))
        profile_data = await ContentProfileService.get_profile_data(session, user.id)
        
        # Редактируем пост через LLM
        from bot.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        
        edited_text = await llm_service.edit_post(
            original_post=post.body,
            edit_instruction=instruction,
            profile_data=profile_data
        )
        
        # Обновляем текст поста
        updated_post = await ContentPostsService.update_post_body(
            session,
            UUID(post_id),
            edited_text
        )
        
        if not updated_post:
            await processing_msg.edit_text("❌ Не удалось обновить пост")
            return
        
        await session.commit()
        
        # Показываем обновленный пост
        from bot.keyboards.keyboards import get_post_actions_keyboard
        
        await processing_msg.edit_text(
            f"{edited_text}\n\n---\n_Обновлённая версия_",
            reply_markup=get_post_actions_keyboard(str(updated_post.id)),
            parse_mode="Markdown"
        )
        
        await state.set_state(ContentMakerStates.post_viewing)
        
    except Exception as e:
        logger.error(f"Ошибка при завершении редактирования поста: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обновлении поста")


# ============ ПЛАНЕР ============

@router.callback_query(F.data == "cm_planner")
async def show_planner(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать планер идей - главное меню с категориями"""
    try:
        await callback.answer()
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        if not user:
            await safe_edit_or_send(callback.message, "❌ Пользователь не найден")
            return
        
        from bot.services.content_ideas_service import ContentIdeasService
        
        # Получаем группировку идей по типам
        grouped_ideas = await ContentIdeasService.get_ideas_grouped_by_type(session, user.id)
        
        if not grouped_ideas:
            await safe_edit_or_send(
                callback.message,
                "📋 *МОЙ ПЛАНЕР ИДЕЙ*\n\nУ тебя пока нет сохраненных идей.\n\nГенерируй новые идеи и сохраняй их!",
                reply_markup=get_back_to_content_maker(),
                parse_mode="Markdown"
            )
            return
        
        # Очищаем предыдущие сообщения
        data = await state.get_data()
        old_messages = data.get('cm_messages_to_delete', [])
        if old_messages:
            await cleanup_messages(callback.bot, callback.message.chat.id, old_messages)
            await state.update_data(cm_messages_to_delete=[])
        
        # Получаем названия типов контента
        categories = {}
        for type_id, count in grouped_ideas.items():
            content_type = await ContentIdeasService.get_content_type_by_id(session, type_id)
            if content_type:
                categories[type_id] = (content_type.name, count)
        
        total_count = sum(grouped_ideas.values())
        
        planner_text = f"📋 *МОЙ ПЛАНЕР ИДЕЙ*\n\nВсего сохранено: {total_count}\n\nВыбери категорию:"
        
        from bot.keyboards.keyboards import get_planner_categories_keyboard
        
        await safe_edit_or_send(
            callback.message,
            planner_text,
            reply_markup=get_planner_categories_keyboard(categories),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отображении планера: {e}", exc_info=True)
        await callback.message.answer(
            "❌ Ошибка при загрузке планера",
            reply_markup=get_back_to_content_maker()
        )


@router.callback_query(F.data.startswith("cm_planner_type_"))
async def show_planner_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать идеи конкретного типа"""
    try:
        await callback.answer()
        
        type_id = int(callback.data.split("_")[-1])
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        if not user:
            await callback.message.edit_text("❌ Пользователь не найден")
            return
        
        from bot.services.content_ideas_service import ContentIdeasService
        
        # Получаем идеи этого типа
        ideas = await ContentIdeasService.get_saved_ideas_by_type(session, user.id, type_id)
        
        if not ideas:
            await callback.message.edit_text(
                "❌ Идеи не найдены",
                reply_markup=get_back_to_content_maker()
            )
            return
        
        # Сохраняем идеи в state
        await state.update_data(
            planner_ideas=[(str(idea.id), idea.title, idea.description or "") for idea in ideas],
            planner_type_id=type_id,
            planner_current_index=0
        )
        
        # Показываем первую идею
        await show_planner_idea_at_index(callback.message, state, 0, ideas, type_id)
        
    except Exception as e:
        logger.error(f"Ошибка при отображении идей типа: {e}", exc_info=True)


async def show_planner_idea_at_index(message: Message, state: FSMContext, index: int, ideas: list, type_id: int):
    """Показать идею из планера по индексу"""
    try:
        if index < 0 or index >= len(ideas):
            return
        
        idea = ideas[index]
        
        idea_text = f"💡 *ИДЕЯ #{index + 1}*\n\n"
        idea_text += f"*{idea.title}*\n\n"
        if idea.description:
            idea_text += f"{idea.description}\n\n"
        idea_text += f"_Сохранено: {idea.created_at.strftime('%d.%m.%Y')}_"
        
        from bot.keyboards.keyboards import get_planner_type_ideas_keyboard
        
        await message.edit_text(
            idea_text,
            reply_markup=get_planner_type_ideas_keyboard(index, len(ideas), str(idea.id), type_id),
            parse_mode="Markdown"
        )
        
        await state.update_data(planner_current_index=index)
        
    except Exception as e:
        logger.error(f"Ошибка при отображении идеи планера: {e}", exc_info=True)


@router.callback_query(F.data.startswith("cm_planner_nav_"))
async def navigate_planner_ideas(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Навигация по идеям в планере"""
    try:
        await callback.answer()
        
        parts = callback.data.split("_")
        type_id = int(parts[3])
        new_index = int(parts[4])
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        if not user:
            return
        
        from bot.services.content_ideas_service import ContentIdeasService
        
        # Получаем идеи этого типа
        ideas = await ContentIdeasService.get_saved_ideas_by_type(session, user.id, type_id)
        
        if not ideas or new_index >= len(ideas):
            return
        
        await show_planner_idea_at_index(callback.message, state, new_index, ideas, type_id)
        
    except Exception as e:
        logger.error(f"Ошибка при навигации по идеям планера: {e}", exc_info=True)


@router.callback_query(F.data == "cm_planner_position")
async def planner_position_click(callback: CallbackQuery):
    """Обработка нажатия на кнопку позиции в планере"""
    await callback.answer()


@router.callback_query(F.data.startswith("cm_delete_idea_"))
async def delete_idea(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Удалить идею из планера"""
    try:
        idea_id = callback.data.replace("cm_delete_idea_", "")
        
        from bot.services.content_ideas_service import ContentIdeasService
        from uuid import UUID
        
        # Получаем текущее состояние для навигации
        data = await state.get_data()
        current_index = data.get('planner_current_index', 0)
        type_id = data.get('planner_type_id')
        
        # Удаляем идею
        await ContentIdeasService.archive_idea(session, UUID(idea_id))
        await session.commit()
        
        await callback.answer("✅ Идея удалена")
        
        # Получаем обновленный список идей
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        if user and type_id:
            ideas = await ContentIdeasService.get_saved_ideas_by_type(session, user.id, type_id)
            
            if not ideas:
                # Если идей больше нет, возвращаемся к категориям
                await callback.message.edit_text(
                    "📋 Все идеи в этой категории удалены",
                    reply_markup=get_back_to_content_maker()
                )
                return
            
            # Корректируем индекс если нужно
            if current_index >= len(ideas):
                current_index = len(ideas) - 1
            
            # Показываем следующую идею
            await show_planner_idea_at_index(callback.message, state, current_index, ideas, type_id)
        
    except Exception as e:
        logger.error(f"Ошибка при удалении идеи: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


@router.callback_query(F.data.startswith("cm_write_from_idea_"))
async def write_post_from_planner_idea(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Написать пост из идеи планера"""
    try:
        await callback.answer()
        
        idea_id = callback.data.replace("cm_write_from_idea_", "")
        
        from bot.services.content_ideas_service import ContentIdeasService
        from uuid import UUID
        
        # Получаем идею
        idea = await ContentIdeasService.get_idea_by_id(session, UUID(idea_id))
        
        if not idea:
            await callback.message.answer("❌ Идея не найдена")
            return
        
        processing_msg = await callback.message.edit_text("⏳ Пишу пост...")
        
        user = await UserService.get_user_by_telegram_id(session, str(callback.from_user.id))
        
        if not user:
            await processing_msg.edit_text("❌ Пользователь не найден")
            return
        
        # Получаем профиль
        profile_data = await ContentProfileService.get_profile_data(session, user.id)
        
        # Генерируем пост
        from bot.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        
        post_text = await llm_service.generate_post(
            profile_data,
            idea.title,
            idea.description or "",
            idea.content_type.name if idea.content_type else "Контент",
            idea.platform or 'telegram'
        )
        
        # Сохраняем пост
        from bot.services.content_posts_service import ContentPostsService
        
        post = await ContentPostsService.create_post(
            session,
            user.id,
            platform=idea.platform or 'telegram',
            body=post_text,
            version=1,
            status='draft'
        )
        
        # Автоматически архивируем идею после создания поста
        await ContentIdeasService.archive_idea(session, UUID(idea_id))
        
        await session.commit()
        
        # Показываем пост
        from bot.keyboards.keyboards import get_post_actions_keyboard
        
        await processing_msg.edit_text(
            f"{post_text}\n\n---\n_Вариант 1 (основной)_",
            reply_markup=get_post_actions_keyboard(str(post.id)),
            parse_mode="Markdown"
        )
        
        await state.update_data(current_post_id=str(post.id))
        await state.set_state(ContentMakerStates.post_viewing)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации поста из планера: {e}", exc_info=True)
        await callback.message.answer("❌ Ошибка при генерации поста")


@router.message(ContentMakerStates.post_custom_idea)
async def process_custom_idea_for_post(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка своей идеи для написания поста"""
    try:
        custom_idea = message.text
        
        if not custom_idea or len(custom_idea) < 10:
            await message.answer("❌ Идея слишком короткая. Опишите подробнее (минимум 10 символов).")
            return
        
        processing_msg = await message.answer("⏳ Пишу пост...")
        
        user = await UserService.get_user_by_telegram_id(session, str(message.from_user.id))
        
        if not user:
            await processing_msg.edit_text("❌ Пользователь не найден")
            return
        
        # Получаем профиль
        profile_data = await ContentProfileService.get_profile_data(session, user.id)
        
        # Генерируем пост из своей идеи
        from bot.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        
        post_text = await llm_service.generate_post(
            profile_data,
            "Своя идея",
            custom_idea,
            "Контент",
            'telegram'
        )
        
        # Сохраняем пост
        from bot.services.content_posts_service import ContentPostsService
        
        post = await ContentPostsService.create_post(
            session,
            user.id,
            platform='telegram',
            body=post_text,
            version=1,
            status='draft'
        )
        
        await session.commit()
        
        # Показываем пост
        from bot.keyboards.keyboards import get_post_actions_keyboard
        
        await processing_msg.edit_text(
            f"{post_text}\n\n---\n_Вариант 1 (основной)_",
            reply_markup=get_post_actions_keyboard(str(post.id)),
            parse_mode="Markdown"
        )
        
        await state.update_data(current_post_id=str(post.id))
        await state.set_state(ContentMakerStates.post_viewing)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации поста из своей идеи: {e}", exc_info=True)
        await message.answer("❌ Ошибка при генерации поста")