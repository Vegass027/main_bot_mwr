from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest

from bot.keyboards.keyboards import get_tourist_menu, get_tourist_back_menu
from bot.services.user_service import UserService
from bot.utils.states import UserStates

router = Router()

TOURIST_INTRO = """Отлично! Мы — закрытый клуб путешественников MWR Life.

У нас цены ниже, чем на Booking, потому что мы работаем по оптовой модели (как Netflix, только для отелей).

Что хочешь узнать?"""

TOURIST_WHY_CHEAPER = """Отели продают номера оптовикам со скидкой до 70%, чтобы не стоять пустыми.

Обычные сайты (Booking, Expedia) добавляют наценку на рекламу.

MWR Life не тратит на рекламу. Мы отдаем эту скидку нашим членам клуба. Вы платите чистую оптовую цену."""

TOURIST_LEGAL = """Абсолютно. Мы работаем с 2013 года в 150 странах мира.

Мы являемся членами ETOA (Европейская туристическая ассоциация) и партнерами IATA.

Это официальная мировая практика закрытых клубов."""

TOURIST_EXAMPLE = """Например: Неделя в отеле 5★ в Дубае.

Booking: 1500€
Travel Advantage: 900€

Ваша выгода: 600€ (одна поездка окупает подписку на годы вперед)."""

@router.callback_query(F.data == "tourist")
async def tourist_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать меню туриста"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Если есть реферер, добавляем событие в радар
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Нажал 'Путешествия'"
        )
    
    try:
        await callback.message.edit_text(
            TOURIST_INTRO,
            reply_markup=get_tourist_menu()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Меню туриста", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.tourist_menu)
    await callback.answer()

@router.callback_query(F.data == "tourist_why_cheaper")
async def tourist_why_cheaper(callback: CallbackQuery, state: FSMContext):
    """Ответ: Почему дешевле?"""
    
    try:
        await callback.message.edit_text(
            TOURIST_WHY_CHEAPER,
            reply_markup=get_tourist_back_menu()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Почему дешевле", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.tourist_why_cheaper)
    await callback.answer()

@router.callback_query(F.data == "tourist_legal")
async def tourist_legal(callback: CallbackQuery, state: FSMContext):
    """Ответ: Легально ли это?"""
    
    try:
        await callback.message.edit_text(
            TOURIST_LEGAL,
            reply_markup=get_tourist_back_menu()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Легальность", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.tourist_legal)
    await callback.answer()

@router.callback_query(F.data == "tourist_example")
async def tourist_example(callback: CallbackQuery, state: FSMContext):
    """Ответ: Пример экономии"""
    
    try:
        await callback.message.edit_text(
            TOURIST_EXAMPLE,
            reply_markup=get_tourist_back_menu()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Пример экономии", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.tourist_example)
    await callback.answer()

@router.callback_query(F.data == "tourist_consultant")
async def tourist_consultant(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Показать контакты консультанта (реферера)"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    if not referrer:
        try:
            await callback.message.edit_text(
                "К сожалению, информация о консультанте недоступна.",
                reply_markup=get_tourist_back_menu()
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Если сообщение не изменилось, просто отправляем ответ на callback
                await callback.answer("Консультант недоступен", show_alert=False)
            else:
                # Если другая ошибка BadRequest, пробрасываем дальше
                raise
        await callback.answer()
        return
    
    # Формируем текст с контактами
    consultant_text = f"Ваш персональный консультант: **{referrer.consultant_name or referrer.first_name or 'Консультант'}**.\n\n"
    consultant_text += "📲 Свяжитесь с ним:\n"
    
    if referrer.consultant_instagram:
        consultant_text += f"📱 Instagram: {referrer.consultant_instagram}\n"
    if referrer.consultant_whatsapp:
        consultant_text += f"💬 WhatsApp: {referrer.consultant_whatsapp}\n"
    if referrer.consultant_telegram:
        consultant_text += f"📱 Telegram: @{referrer.consultant_telegram}\n"
    if referrer.consultant_email:
        consultant_text += f"📧 Email: {referrer.consultant_email}\n"
    if referrer.consultant_phone:
        consultant_text += f"📞 Phone: {referrer.consultant_phone}\n"
    
    # Добавляем событие в радар
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Запросил контакты консультанта"
        )
    
    try:
        await callback.message.edit_text(
            consultant_text,
            reply_markup=get_tourist_back_menu()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Контакты консультанта", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.tourist_consultant)
    await callback.answer()