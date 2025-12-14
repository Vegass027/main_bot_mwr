from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession


from bot.keyboards.keyboards import get_back_to_pro_menu, get_ai_designer_menu, get_ai_designer_control_panel
from bot.services.user_service import UserService
from bot.services.ai_designer_service import AIDesignerService
from bot.utils.states import UserStates
import logging


router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "ai_designer")
async def ai_designer_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Вход в AI-Designer"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Проверка PRO статуса
    if user.subscription_status != 'PRO':
        await callback.answer("⚠️ AI-Дизайнер доступен только для PRO пользователей", show_alert=True)
        return
    
    welcome_text = """🎨 **AI-Дизайнер**

🆕 **Режим 1: Генерация**

Напиши что хочешь → получи фото

---------

✏️ **Режим 2: Редактирование**

Ответь (Reply) на фото бота → напиши что изменить

---------

🎭 **Режим 3: Трансформация**

Загрузи своё фото + напиши что изменить

---------

🎬 **Режим 4: Replay**

Ответь (Reply) на фото бота + загрузи своё фото → добавлю тебя в сцену

💬 Готов?  Жду команду! 👇"""
    
    try:
        await callback.message.edit_text(
            welcome_text,
            reply_markup=get_ai_designer_menu(),
            parse_mode="Markdown"
        )
    except Exception:
        # Игнорируем ошибку если сообщение не изменилось
        pass
    
    await state.set_state(UserStates.ai_designer_active)
    await callback.answer()


@router.message(UserStates.ai_designer_active, F.text)
async def handle_text_request(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработка текстового запроса
    Режим 1: Текст → Картинка
    Режим 2: Правка картинки (если это reply)
    """
    
    telegram_id = str(message.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    logger.info(
        f"Text handler triggered",
        extra={
            "user_id": telegram_id,
            "has_reply": message.reply_to_message is not None,
            "reply_has_photo": message.reply_to_message and message.reply_to_message.photo is not None,
            "text": message.text[:50] if message.text else None
        }
    )
    
    # Проверка PRO статуса
    if user.subscription_status != 'PRO':
        await message.answer("⚠️ AI-Дизайнер доступен только для PRO пользователей")
        return
    
    # Проверяем, это reply или нет
    if message.reply_to_message and message.reply_to_message.photo:
        # Режим 2: Правка картинки
        logger.info("Routing to: handle_image_edit (Agent 2)")
        await handle_image_edit(message, state, session, user)
    else:
        # Режим 1: Текст → Картинка
        logger.info("Routing to: handle_text_to_image (Agent 1)")
        await handle_text_to_image(message, state, session, user)


async def handle_text_to_image(message: Message, state: FSMContext, session: AsyncSession, user):
    """АГЕНТ 1: Генерация изображения из текста"""
    
    processing_msg = await message.answer(
        "🎨 **Генерирую изображение...**\n⏱ Это займёт 10-30 секунд",
        parse_mode="Markdown"
    )
    
    try:
        # Генерируем изображение (пока без сохранения - нам нужен ID сообщения бота)
        prompt = await AIDesignerService.generate_prompt_with_openai(
            message.text,
            case_type="A"
        )
        
        image_url = await AIDesignerService.generate_image_with_flux_edit(prompt)
        
        # Удаляем служебные сообщения
        try:
            await message.delete()  # Удаляем запрос пользователя
            await processing_msg.delete()  # Удаляем статус
        except:
            pass
        
        # Отправляем результат с постоянной панелью
        result_msg = await message.answer_photo(
            photo=image_url,
            caption="✅ **Готово!**\n\n💡 Хочешь изменить? Ответь (Reply) на это фото с точным описанием!",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        
        # ТЕПЕРЬ сохраняем с ID сообщения БОТА
        await AIDesignerService.save_generation(
            session,
            user.id,
            str(result_msg.message_id),
            prompt,
            image_url,
            "text_to_image"
        )
        
    except Exception as e:
        logger.error(f"Ошибка генерации (Агент 1): {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        
        # Экранируем спецсимволы для Markdown
        error_msg = str(e).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        await message.answer(
            f"❌ **Ошибка генерации**\n\n`{error_msg}`\n\nПопробуй другой запрос.",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )


async def handle_image_edit(message: Message, state: FSMContext, session: AsyncSession, user):
    """АГЕНТ 2: Редактирование существующего изображения"""
    
    processing_msg = await message.answer(
        "✏️ **Редактирую изображение...**\n⏱ Это займёт 10-30 секунд",
        parse_mode="Markdown"
    )
    
    try:
        reply_message_id = str(message.reply_to_message.message_id)
        
        # Получаем старую генерацию
        old_generation = await AIDesignerService.get_generation_by_message_id(
            session,
            reply_message_id
        )
        
        if not old_generation:
            raise ValueError("Старая генерация не найдена или истекла (48 часов)")
        
        # Улучшаем промпт редактирования
        edit_prompt = await AIDesignerService.enhance_edit_prompt_with_llm(message.text)
        
        # Генерируем
        image_url = await AIDesignerService.generate_image_with_flux_edit(
            edit_prompt,
            image_url=old_generation.image_url
        )
        
        # Удаляем служебные сообщения
        try:
            await message.delete()  # Удаляем запрос пользователя
            await processing_msg.delete()  # Удаляем статус
        except:
            pass
        
        # Отправляем результат с панелью
        result_msg = await message.answer_photo(
            photo=image_url,
            caption="✅ **Изменения применены!**\n\n💡 Продолжай редактировать? Ответь (Reply) на это фото!",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        
        # Сохраняем с ID сообщения БОТА
        await AIDesignerService.save_generation(
            session,
            user.id,
            str(result_msg.message_id),
            edit_prompt,
            image_url,
            "image_to_image_edit"
        )
        
    except ValueError as e:
        try:
            await processing_msg.delete()
        except:
            pass
        await message.answer(
            f"⚠️ {str(e)}",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка редактирования (Агент 2): {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        await message.answer(
            f"❌ **Ошибка редактирования**\n\n{str(e)}\n\nПопробуй точнее описать изменения.",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )


@router.message(UserStates.ai_designer_active, F.photo)
async def handle_photo_transformation(message: Message, state: FSMContext, session: AsyncSession):
    """
    АГЕНТ 3: Трансформация фото по референсу (с LLM)
    АГЕНТ 4 (НОВЫЙ): Replay - добавление пользователя на сгенерированное фото
    АГЕНТ 2 (АЛЬТЕРНАТИВНЫЙ): Редактирование через reply на фото с фото в caption
    """
    
    telegram_id = str(message.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    logger.info(
        f"Photo handler triggered",
        extra={
            "user_id": telegram_id,
            "has_reply": message.reply_to_message is not None,
            "reply_has_photo": message.reply_to_message and message.reply_to_message.photo is not None,
            "has_caption": message.caption is not None,
            "caption": message.caption[:50] if message.caption else None,
            "reply_message_type": type(message.reply_to_message).__name__ if message.reply_to_message else None,
            "reply_message_content": f"photo={message.reply_to_message.photo is not None}, text={message.reply_to_message.text is not None}" if message.reply_to_message else None
        }
    )
    
    # Проверка PRO статуса
    if user.subscription_status != 'PRO':
        await message.answer(
            "⚠️ AI-Дизайнер доступен только для PRO пользователей",
            reply_markup=get_ai_designer_control_panel()
        )
        return
    
    # Проверяем - это reply на сгенерированное фото или нет
    # ВАЖНО: Проверяем наличие caption ПЕРЕД проверкой reply_to_message
    # Если есть caption - это редактирование (Агент 2)
    if message.caption and message.reply_to_message and message.reply_to_message.photo:
        # АГЕНТ 2 (АЛЬТЕРНАТИВНЫЙ): Редактирование через reply на фото с фото
        # Пользователь отправил фото в ответ на сгенерированное фото с описанием
        logger.info("Routing to: handle_image_edit_with_reference_photo (Agent 2 alt)")
        await handle_image_edit_with_reference_photo(message, state, session, user)
    elif message.reply_to_message and message.reply_to_message.photo:
        # АГЕНТ 4: Replay - добавление себя на сгенерированное фото
        logger.info("Routing to: handle_replay_with_user_photo (Agent 4)")
        await handle_replay_with_user_photo(message, state, session, user)
    else:
        # АГЕНТ 3: Обычная трансформация фото
        logger.info("Routing to: handle_standard_photo_transformation (Agent 3)")
        await handle_standard_photo_transformation(message, state, session, user)


async def handle_image_edit_with_reference_photo(message: Message, state: FSMContext, session: AsyncSession, user):
    """АГЕНТ 2 (АЛЬТЕРНАТИВНЫЙ): Редактирование через reply на фото с фото-референсом"""
    
    processing_msg = await message.answer(
        "✏️ **Редактирую изображение с референсом...**\n⏱ Это займёт 10-30 секунд",
        parse_mode="Markdown"
    )
    
    try:
        reply_message_id = str(message.reply_to_message.message_id)
        
        # Получаем старую генерацию
        old_generation = await AIDesignerService.get_generation_by_message_id(
            session,
            reply_message_id
        )
        
        if not old_generation:
            raise ValueError("Старая генерация не найдена или истекла (48 часов)")
        
        # Получаем URL фото пользователя (референс)
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        reference_photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
        
        # Улучшаем промпт редактирования с учётом референса
        edit_prompt = await AIDesignerService.enhance_edit_prompt_with_llm(
            f"{message.caption} (Reference photo provided for style/composition guidance)"
        )
        
        # Генерируем с обоими изображениями
        image_url = await AIDesignerService.generate_image_with_flux_edit(
            edit_prompt,
            image_urls=[old_generation.image_url, reference_photo_url]
        )
        
        # Удаляем служебные сообщения
        try:
            await message.delete()
            await processing_msg.delete()
        except:
            pass
        
        # Отправляем результат с панелью
        result_msg = await message.answer_photo(
            photo=image_url,
            caption="✅ **Изменения применены!**\n\n💡 Продолжай редактировать? Ответь (Reply) на это фото!",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        
        # Сохраняем с ID сообщения БОТА
        await AIDesignerService.save_generation(
            session,
            user.id,
            str(result_msg.message_id),
            edit_prompt,
            image_url,
            "image_to_image_edit"
        )
        
    except ValueError as e:
        try:
            await processing_msg.delete()
        except:
            pass
        await message.answer(
            f"⚠️ {str(e)}",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка редактирования с референсом (Агент 2 альт): {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        await message.answer(
            f"❌ **Ошибка редактирования**\n\n{str(e)}\n\nПопробуй точнее описать изменения.",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )


async def handle_standard_photo_transformation(message: Message, state: FSMContext, session: AsyncSession, user):
    """АГЕНТ 3: Стандартная трансформация фото по референсу"""
    
    # Проверяем наличие caption
    if not message.caption:
        await message.answer(
            "⚠️ **Добавь описание к фото!**\n\n"
            "Примеры:\n"
            "• \"Перенеси меня на пляж Мальдив\"\n"
            "• \"Сделай фон космическим\"\n"
            "• \"Превращение в супергероя\"",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        return
    
    processing_msg = await message.answer(
        "🎭 **Трансформирую по референсу...**\n⏱ Это займёт 10-30 секунд",
        parse_mode="Markdown"
    )
    
    try:
        # Получаем URL фото
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
        
        # Генерируем промпт трансформации
        transform_prompt = await AIDesignerService.generate_prompt_with_openai(
            f"Transform this image: {message.caption}",
            case_type="C"
        )
        
        # Генерируем изображение
        image_url = await AIDesignerService.generate_image_with_flux_edit(
            transform_prompt,
            image_url=photo_url
        )
        
        # Удаляем служебные сообщения
        try:
            await message.delete()
            await processing_msg.delete()
        except:
            pass
        
        # Отправляем результат с панелью
        result_msg = await message.answer_photo(
            photo=image_url,
            caption="✨ **Трансформация завершена!**\n\n💡 Хочешь добавить себя на эту картинку? Ответь (Reply) на неё с твоим фото!",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        
        # Сохраняем с ID сообщения БОТА
        await AIDesignerService.save_generation(
            session,
            user.id,
            str(result_msg.message_id),
            transform_prompt,
            image_url,
            "image_to_image_transform"
        )
        
    except Exception as e:
        logger.error(f"Ошибка трансформации (Агент 3): {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        
        error_msg = str(e).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        await message.answer(
            f"❌ **Ошибка трансформации**\n\n`{error_msg}`\n\nПопробуй другое фото или описание.",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )


async def handle_replay_with_user_photo(message: Message, state: FSMContext, session: AsyncSession, user):
    """АГЕНТ 4: Replay - добавление пользователя на сгенерированное изображение"""
    
    # Проверяем наличие caption
    if not message.caption:
        await message.answer(
            "⚠️ **Добавь описание к фото!**\n\n"
            "Примеры:\n"
            "• \"Добавь меня на эту фотографию\"\n"
            "• \"Поместите меня в этот интерьер\"\n"
            "• \"Я хочу быть в этом месте\"",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        return
    
    processing_msg = await message.answer(
        "🎬 **Добавляю тебя на изображение...**\n⏱ Это займёт 15-40 секунд",
        parse_mode="Markdown"
    )
    
    try:
        reply_message_id = str(message.reply_to_message.message_id)
        
        # Получаем оригинальную генерацию
        original_generation = await AIDesignerService.get_generation_by_message_id(
            session,
            reply_message_id
        )
        
        if not original_generation:
            raise ValueError("Оригинальная генерация не найдена или истекла (48 часов)")
        
        # Получаем URL фото пользователя
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        user_photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
        
        # Оптимизируем промпт
        replay_prompt = await AIDesignerService.enhance_replay_prompt_with_llm(message.caption)
        
        # Генерируем
        image_url = await AIDesignerService.generate_image_with_flux_edit(
            replay_prompt,
            image_urls=[original_generation.image_url, user_photo_url]
        )
        
        # Удаляем служебные сообщения
        try:
            await message.delete()
            await processing_msg.delete()
        except:
            pass
        
        # Отправляем результат с панелью
        result_msg = await message.answer_photo(
            photo=image_url,
            caption="🎬 **Готово! Ты добавлен на изображение!**\n\n💡 Хочешь ещё изменений? Ответь (Reply) на это фото!",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        
        # Сохраняем с ID сообщения БОТА
        await AIDesignerService.save_generation(
            session,
            user.id,
            str(result_msg.message_id),
            replay_prompt,
            image_url,
            "image_to_image_replay"
        )
        
    except ValueError as e:
        try:
            await processing_msg.delete()
        except:
            pass
        await message.answer(
            f"⚠️ {str(e)}",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка replay (Агент 4): {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        
        error_msg = str(e).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        await message.answer(
            f"❌ **Ошибка добавления на изображение**\n\n`{error_msg}`\n\nПопробуй другое фото или описание.",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "ai_designer_examples")
async def show_examples(callback: CallbackQuery):
    """Показать примеры запросов"""
    
    examples_text = """💡**Как использовать AI-Дизайнера**

🆕 **Агент 1: Генерация**

Просто опиши что хочешь — промпт улучшится автоматически.

Пример:
• Девушка в кафе
• Скандинавский интерьер

---------

✏️ **Агент 2: Редактирование**

Пример:
• добавь кактус
• сделай волосы блондинистыми

---------

🎭 **Агент 3: Трансформация**

Пример:
• Перенеси меня на пляж
• Сделай фон космическим

---------

🎬 **Агент 4: Replay**

Работа с историей:

• Генерируешь сцену: "Пентхаус с видом на город"
• Открываешь Историю → выбираешь фото → Reply
• Загружаешь своё фото: "Добавь меня сюда"

---------

⚡️ **Как это работает:**

📝 Отправляешь сырой запрос или описываешь детально
🤖 Промпт улучшается профессионально
✨ Только потом выполняется генерация

💾 Все изображения в Истории — можешь сделать Reply на любое"""
    
    await callback.message.answer(
        examples_text,
        reply_markup=get_ai_designer_control_panel(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "ai_designer_history")
async def show_history(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать историю генераций пользователя (первое изображение)"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Проверка PRO статуса
    if user.subscription_status != 'PRO':
        await callback.answer("⚠️ AI-Дизайнер доступен только для PRO пользователей", show_alert=True)
        return
    
    # Получаем последние 50 генераций
    generations = await AIDesignerService.get_user_generations(session, user.id, limit=50)
    
    if not generations:
        await callback.answer("📭 У вас пока нет сохранённых генераций", show_alert=True)
        return
    
    # Показываем первое изображение
    await show_history_page(callback.message, session, user.id, 0, edit=True)
    await callback.answer()


async def show_history_page(message, session: AsyncSession, user_id, page: int, edit: bool = False):
    """Показать конкретную страницу истории"""
    
    # Получаем генерации
    generations = await AIDesignerService.get_user_generations(session, user_id, limit=50)
    
    if not generations or page < 0 or page >= len(generations):
        return
    
    gen = generations[page]
    
    # Краткое описание
    mode_emoji = {
        "text_to_image": "🆕",
        "image_to_image_edit": "✏️",
        "image_to_image_transform": "🎭",
        "image_to_image_replay": "🎬"
    }
    mode_name = {
        "text_to_image": "Генерация",
        "image_to_image_edit": "Редактирование",
        "image_to_image_transform": "Трансформация",
        "image_to_image_replay": "Replay"
    }
    
    caption = f"📜 **История генераций** ({page + 1}/{len(generations)})\n\n{mode_emoji.get(gen.mode, '🎨')} **{mode_name.get(gen.mode, 'AI')}**\n_{gen.created_at.strftime('%d.%m.%Y %H:%M')}_"
    
    # Создаем кнопки навигации
    buttons = []
    nav_row = []
    
    # Кнопка "Назад" (предыдущее фото)
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"history_page_{page-1}"))
    
    # Счетчик
    nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{len(generations)}", callback_data="noop"))
    
    # Кнопка "Вперед" (следующее фото)
    if page < len(generations) - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"history_page_{page+1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Кнопка Replay
    buttons.append([InlineKeyboardButton(text="🎬 Replay", callback_data=f"replay_select_{gen.id}")])
    
    # Кнопка возврата
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_pro")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Обновляем или отправляем сообщение
    if edit:
        try:
            await message.edit_media(
                media=InputMediaPhoto(media=gen.image_url, caption=caption, parse_mode="Markdown"),
                reply_markup=keyboard
            )
        except:
            # Если не получилось отредактировать, отправляем новое
            await message.answer_photo(
                photo=gen.image_url,
                caption=caption,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    else:
        await message.answer_photo(
            photo=gen.image_url,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("history_page_"))
async def navigate_history(callback: CallbackQuery, session: AsyncSession):
    """Навигация по истории"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Получаем номер страницы
    page = int(callback.data.split("_")[-1])
    
    # Получаем генерации
    generations = await AIDesignerService.get_user_generations(session, user.id, limit=50)
    
    if not generations or page < 0 or page >= len(generations):
        await callback.answer("❌ Страница не найдена")
        return
    
    gen = generations[page]
    
    # Краткое описание
    mode_emoji = {
        "text_to_image": "🆕",
        "image_to_image_edit": "✏️",
        "image_to_image_transform": "🎭",
        "image_to_image_replay": "🎬"
    }
    mode_name = {
        "text_to_image": "Генерация",
        "image_to_image_edit": "Редактирование",
        "image_to_image_transform": "Трансформация",
        "image_to_image_replay": "Replay"
    }
    
    caption = f"📜 **История генераций** ({page + 1}/{len(generations)})\n\n{mode_emoji.get(gen.mode, '🎨')} **{mode_name.get(gen.mode, 'AI')}**\n_{gen.created_at.strftime('%d.%m.%Y %H:%M')}_"
    
    # Создаем кнопки навигации
    buttons = []
    nav_row = []
    
    # Кнопка "Назад" (предыдущее фото)
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"history_page_{page-1}"))
    
    # Счетчик
    nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{len(generations)}", callback_data="noop"))
    
    # Кнопка "Вперед" (следующее фото)
    if page < len(generations) - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"history_page_{page+1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Кнопка Replay
    buttons.append([InlineKeyboardButton(text="🎬 Replay", callback_data=f"replay_select_{gen.id}")])
    
    # Кнопка возврата
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_pro")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Обновляем сообщение с новым фото
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(media=gen.image_url, caption=caption, parse_mode="Markdown"),
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка обновления истории: {e}")
        await callback.answer("❌ Ошибка загрузки изображения")
        return
    
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    """Обработчик для кнопки-заглушки"""
    await callback.answer()


@router.callback_query(F.data.startswith("replay_select_"))
async def select_for_replay(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор изображения для replay из истории"""
    
    generation_id = callback.data.split("_", 2)[2]
    
    # Сохраняем ID выбранной генерации в state
    await state.update_data(selected_generation_id=generation_id)
    await state.set_state(UserStates.ai_designer_awaiting_replay_photo)
    
    await callback.message.answer(
        "🎬 **Отлично!**\n\n"
        "Теперь отправь своё фото с описанием:\n\n"
        "Примеры:\n"
        "• \"Добавь меня на эту картинку\"\n"
        "• \"Поставь меня в этот интерьер\"\n"
        "• \"Я хочу быть в этом месте\"",
        reply_markup=get_ai_designer_control_panel(),
        parse_mode="Markdown"
    )
    
    await callback.answer()


@router.message(UserStates.ai_designer_awaiting_replay_photo, F.text)
async def handle_replay_text_reminder(message: Message, state: FSMContext):
    """Напоминание отправить фото для replay"""
    
    await message.answer(
        "⚠️ **Нужно отправить ФОТО с описанием!**\n\n"
        "📸 Загрузи своё фото + добавь описание (caption):\n\n"
        "Примеры:\n"
        "• \"Добавь меня на эту картинку\"\n"
        "• \"Поставь меня в этот интерьер\"\n"
        "• \"Я хочу быть в этом месте\"\n\n"
        "❌ Или нажми кнопку ниже, чтобы отменить",
        reply_markup=get_ai_designer_control_panel(),
        parse_mode="Markdown"
    )


@router.message(UserStates.ai_designer_awaiting_replay_photo, F.photo)
async def handle_replay_from_history(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка replay из истории - пользователь отправил своё фото"""
    
    telegram_id = str(message.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Проверка PRO статуса
    if user.subscription_status != 'PRO':
        await message.answer("⚠️ AI-Дизайнер доступен только для PRO пользователей")
        await state.set_state(UserStates.ai_designer_active)
        return
    
    # Проверяем наличие caption
    if not message.caption:
        await message.answer(
            "⚠️ **Добавь описание к фото!**\n\n"
            "Примеры:\n"
            "• \"Добавь меня на эту картинку\"\n"
            "• \"Поставь меня в этот интерьер\"",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        return
    
    # Получаем ID выбранной генерации
    data = await state.get_data()
    selected_generation_id = data.get("selected_generation_id")
    
    if not selected_generation_id:
        await message.answer(
            "⚠️ Произошла ошибка. Выбери изображение из истории снова.",
            reply_markup=get_ai_designer_control_panel()
        )
        await state.set_state(UserStates.ai_designer_active)
        return
    
    processing_msg = await message.answer(
        "🎬 **Добавляю тебя на изображение...**\n⏱ Это займёт 15-40 секунд",
        parse_mode="Markdown"
    )
    
    try:
        # Получаем оригинальную генерацию
        original_generation = await AIDesignerService.get_generation_by_id(
            session,
            selected_generation_id
        )
        
        if not original_generation:
            raise ValueError("Выбранное изображение не найдено или истекло (48 часов)")
        
        # Получаем URL фото пользователя
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        user_photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"
        
        # Оптимизируем промпт
        replay_prompt = await AIDesignerService.enhance_replay_prompt_with_llm(message.caption)
        
        # Генерируем
        image_url = await AIDesignerService.generate_image_with_flux_edit(
            replay_prompt,
            image_urls=[original_generation.image_url, user_photo_url]
        )
        
        # Удаляем служебные сообщения
        try:
            await message.delete()
            await processing_msg.delete()
        except:
            pass
        
        # Отправляем результат
        result_msg = await message.answer_photo(
            photo=image_url,
            caption="🎬 **Готово! Ты добавлен на изображение!**\n\n💡 Хочешь ещё изменений? Ответь (Reply) на это фото!",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        
        # Сохраняем с ID сообщения БОТА
        await AIDesignerService.save_generation(
            session,
            user.id,
            str(result_msg.message_id),
            replay_prompt,
            image_url,
            "image_to_image_replay"
        )
        
        # Возвращаем в активный режим
        await state.set_state(UserStates.ai_designer_active)
        
    except ValueError as e:
        try:
            await processing_msg.delete()
        except:
            pass
        await message.answer(
            f"⚠️ {str(e)}",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        await state.set_state(UserStates.ai_designer_active)
    except Exception as e:
        logger.error(f"Ошибка replay из истории: {e}")
        try:
            await processing_msg.delete()
        except:
            pass
        
        error_msg = str(e).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        await message.answer(
            f"❌ **Ошибка**\n\n`{error_msg}`",
            reply_markup=get_ai_designer_control_panel(),
            parse_mode="Markdown"
        )
        await state.set_state(UserStates.ai_designer_active)


@router.callback_query(UserStates.ai_designer_awaiting_replay_photo, F.data == "back_to_pro")
async def cancel_replay_and_back_to_designer(callback: CallbackQuery, state: FSMContext):
    """Отмена ожидания фото для replay и возврат в AI-Designer"""
    
    # Возвращаемся в активный режим AI-Designer
    await state.set_state(UserStates.ai_designer_active)
    
    # Очищаем сохранённый ID генерации
    await state.update_data(selected_generation_id=None)
    
    await callback.message.answer(
        "❌ **Replay отменён**\n\n"
        "💬 Можешь продолжить работу с AI-Дизайнером!",
        reply_markup=get_ai_designer_control_panel(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_pro")
async def back_to_pro_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в PRO меню"""
    
    # Импортируем здесь чтобы избежать циклических импортов
    from bot.keyboards.keyboards import get_pro_menu
    
    # Удаляем фото и отправляем новое текстовое
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(
        "🎯 **PRO Панель**\n\nВыбери инструмент:",
        reply_markup=get_pro_menu(),
        parse_mode="Markdown"
    )
    await state.set_state(UserStates.pro_menu)
    await callback.answer()
