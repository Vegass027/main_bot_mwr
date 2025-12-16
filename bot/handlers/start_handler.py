from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest

from bot.keyboards.keyboards import get_guest_menu, get_pro_menu
from bot.services.user_service import UserService
from bot.utils.states import UserStates

router = Router()

WELCOME_TEXT = """Привет! 👋 Я твой цифровой помощник.

Я помогаю людям путешествовать в отелях 5★ по цене 3★ и превращать поездки в источник дохода.

Я не знаю, что тебе интереснее сейчас: просто сэкономить на отпуске или заработать на этом рынке.

**Сделай свой выбор в меню ниже** 👇"""

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """Обработчик команды /start с реферальной логикой"""
    
    telegram_id = str(message.from_user.id)
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Извлекаем реферальный код из deep link
    referral_code = None
    if message.text and len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
    
    # Получаем username бота
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    # Получаем или создаем пользователя
    user = await UserService.get_or_create_user(
        session=session,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referral_code=referral_code,
        bot_username=bot_username
    )
    
    # Проверяем наличие реферера и его приветственного видео
    referrer = await UserService.get_referrer(session, user)
    
    if referrer and referrer.welcome_video_id:
        # Отправляем видео-кружочек реферера
        await message.answer_video_note(
            video_note=referrer.welcome_video_id
        )
        # Добавляем текст под видео с кнопками
        await message.answer(
            "Что вас интересует?",
            reply_markup=get_guest_menu() if user.subscription_status == 'FREE' else get_pro_menu()
        )
    else:
        # Отправляем стандартное текстовое приветствие с кнопками
        if user.subscription_status == 'PRO':
            # Для PRO пользователей - краткое приветствие
            await message.answer(
                "**Привет, как успехи?n\nЧем займемся?👀",
                reply_markup=get_pro_menu()
            )
        else:
            # Для обычных пользователей - полное приветствие
            await message.answer(
                f"{WELCOME_TEXT}\n\nЧто вас интересует?",
                reply_markup=get_guest_menu(),
                parse_mode="Markdown"
            )
    
    # Устанавливаем состояние
    if user.subscription_status == 'FREE':
        await state.set_state(UserStates.guest_menu)
    else:
        await state.set_state(UserStates.pro_menu)

@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Возврат в главное меню"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    try:
        await callback.message.edit_text(
            "Что вас интересует?",
            reply_markup=get_guest_menu() if user.subscription_status == 'FREE' else get_pro_menu()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e) or "there is no text in the message to edit" in str(e):
            # Если сообщение не изменилось или нет текста для редактирования, отправляем новое сообщение
            await callback.message.answer(
                "Что вас интересует?",
                reply_markup=get_guest_menu() if user.subscription_status == 'FREE' else get_pro_menu()
            )
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    if user.subscription_status == 'FREE':
        await state.set_state(UserStates.guest_menu)
    else:
        await state.set_state(UserStates.pro_menu)
    
    await callback.answer()

@router.callback_query(F.data == "back_to_pro_menu")
async def back_to_pro_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в PRO меню"""
    
    try:
        await callback.message.edit_text(
            "С возвращением, Партнер!\n\nТвои инструменты готовы🔥",
            reply_markup=get_pro_menu(),
            parse_mode="Markdown"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Вы в PRO меню", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.pro_menu)
    await callback.answer()

@router.callback_query(F.data == "my_referral_link")
async def show_referral_link(callback: CallbackQuery, session: AsyncSession):
    """Показать реферальную ссылку PRO пользователю"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if not user:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)
        return
    
    if user.subscription_status != 'PRO':
        await callback.answer("Эта функция доступна только PRO пользователям", show_alert=True)
        return
    
    referral_link = user.telegram_bot_referral_link
    referral_code = user.referral_code
    total_referrals = user.total_referrals or 0
    
    if not referral_link:
        await callback.answer("Ошибка: реферальная ссылка не создана", show_alert=True)
        return
    
    text = f"🔗 Ваша реферальная ссылка:\n\n`{referral_link}`\n\n📊 Статистика:\n\n→ Приглашенных пользователей: {total_referrals}"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_pro_menu(),
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Ваша реферальная ссылка:", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await callback.answer()