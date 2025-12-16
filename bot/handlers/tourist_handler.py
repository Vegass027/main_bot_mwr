import asyncio
from pathlib import Path

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.exceptions import TelegramBadRequest

from bot.keyboards.keyboards import get_tourist_menu, get_tourist_back_menu, get_travel_branch_menu
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
    """Показать меню выбора ветки путешествий"""
    
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
    
    # Отправляем изображение с текстом
    image_path = Path("Travel.jpg")
    if image_path.exists():
        photo = FSInputFile(image_path)
        
        # Текст для ветки путешествий
        travel_branch_text = """**Уважаю твой выбор. Отдыхать — не работать 😉**
        
Смотри, в туризме есть два лагеря:
        
1️⃣ **Туристы** — кормят Booking, Островок, Яндекс и турагентов, переплачивая за рекламу и комиссии.
        
2️⃣ **Путешественники (мы)** — берем те же отели по оптовым ценам напрямую. Без наценок.
        
На картинке выше ☝️ — реальный пример, сколько денег улетает в трубу, если не знать, где бронировать.
        
Чтобы я показал, как это сработает именно для тебя, скажи: **что тебе сейчас важнее всего?** 👇"""
        
        try:
            await callback.message.answer_photo(
                photo=photo,
                caption=travel_branch_text,
                reply_markup=get_travel_branch_menu(),
                parse_mode="Markdown"
            )
            # Удаляем старое сообщение, если оно было
            try:
                await callback.message.delete()
            except:
                pass  # Если не удалось удалить, не страшно
        except Exception as e:
            # Если не удалось отправить фото, отправляем просто текст
            await callback.message.edit_text(
                travel_branch_text,
                reply_markup=get_travel_branch_menu(),
                parse_mode="Markdown"
            )
    else:
        # Если изображение не найдено, отправляем просто текст
        travel_branch_text = """**Уважаю твой выбор. Отдыхать — не работать 😉**
        
Смотри, в туризме есть два лагеря:
        
1️⃣ **Туристы** — кормят Booking, Островок, Яндекс и турагентов, переплачивая за рекламу и комиссии.
        
2️⃣ **Путешественники (мы)** — берем те же отели по оптовым ценам напрямую. Без наценок.
        
На картинке выше ☝️ — реальный пример, сколько денег улетает в трубу, если не знать, где бронировать.
        
Чтобы я показал, как это сработает именно для тебя, скажи: **что тебе сейчас важнее всего?** 👇"""
        
        try:
            await callback.message.edit_text(
                travel_branch_text,
                reply_markup=get_travel_branch_menu(),
                parse_mode="Markdown"
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Если сообщение не изменилось, просто отправляем ответ на callback
                await callback.answer("Выбор ветки путешествий", show_alert=False)
            else:
                # Если другая ошибка BadRequest, пробрасываем дальше
                raise
    
    await state.set_state(UserStates.travel_branch_selection)
    await callback.answer()

# Обработчики для новых веток путешествий
@router.callback_query(F.data == "travel_pay_less")
async def travel_pay_less(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Ветка 'Платить меньше'"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Выбрал: Платить меньше"
        )
    
    # Текст для ветки "Платить меньше"
    pay_less_text = """**Математика простая:**

🏨 Отель хочет заработать хоть что-то, вместо 0.
🛍 Мы выкупаем номера оптом.
🤝 Ты получаешь цену без накруток посредников.

**Пример на пальцах:**
Это как покупать колу в ресторане за 200₽ или на оптовой базе за 40₽. Вкус тот же. Банка та же. Цена разная.

Я собрал для тебя **реальные примеры** с нашей платформы в сравнении с Booking и Островком. Взгляни 👇"""
    
    try:
        await callback.message.edit_text(pay_less_text)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Платить меньше", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_pay_less_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_pay_less_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "Ты должен это увидеть🤯",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Показать примеры цен", web_app=WebAppInfo(url="https://clubsmarttravel.vercel.app/"))]
        ])
    )
    
    await state.set_state(UserStates.travel_pay_less)
    await callback.answer()

@router.callback_query(F.data == "travel_5star_3star")
async def travel_5star_3star(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Ветка 'Жить в 5★ по цене 3★'"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Выбрал: Жить в 5★ по цене 3★"
        )
    
    # Текст для ветки "Жить в 5★ по цене 3★"
    five_star_text = """**Не переплачивай за комфорт 🙅‍♂️**

В туризме самая дикая наценка именно на дорогих турах. Агенты и сайты накручивают туда до 300%. Мы эту накрутку убираем.

**Что тебе открывается:**

✨ **Топовые отели** (уровня Rixos, Hilton, Radisson) по цене обычных "четверок".
🏝 **Авторские туры** — наши закрытые поездки, где уже всё включено на максималках: проживание, экскурсии, вечеринки.
🛥 **Круизы и Курорты** — недоступные для обычных туристов цены.

Я хочу показать тебе реальные примеры, чтобы ты увидел разницу своими глазами.

Жми кнопку ниже 👇"""
    
    try:
        await callback.message.edit_text(five_star_text)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Жить в 5★ по цене 3★", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_5star_3star_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_5star_3star_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "Ты только глянь🤩",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Показать премиум отдых", web_app=WebAppInfo(url="https://clubsmarttravel.vercel.app/"))]
        ])
    )
    
    await state.set_state(UserStates.travel_5star_3star)
    await callback.answer()

@router.callback_query(F.data == "travel_more")
async def travel_more(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Ветка 'Путешествовать чаще'"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Выбрал: Путешествовать чаще"
        )
    
    # Текст для ветки "Путешествовать чаще"
    travel_more_text = """**Путешествия станут неизбежными ✈️**

Проблема не во времени. Проблема в том, что мы вечно откладываем жизнь и бюджет "на потом". Мы решили это через умную систему накоплений.

**Как это работает:**

🔄 **Твоя тревел-копилка:** Ты не платишь «за сервис», а просто ежемесячно откладываешь небольшую сумму себе же на путешествие.
💰 Всё возвращается: 100% твоих денег моментально падают на твой счет в виде баллов.
📈 Свобода действий: Баллы не сгорают. Они копятся столько, сколько нужно, пока ты не решишь полететь. Курс простой: 1 балл = 1$

В итоге: ты просто живешь, а бюджет на отпуск формируется сам собой. 3-4 поездки в год становятся твоей новой нормой.

Жми кнопку, покажу механику подробнее 👇"""
    
    try:
        await callback.message.edit_text(travel_more_text)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Путешествовать чаще", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_travel_more_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_travel_more_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "Смотри👀",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✈️ Как это работает?", web_app=WebAppInfo(url="https://clubsmarttravel.vercel.app/"))]
        ])
    )
    
    await state.set_state(UserStates.travel_more)
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