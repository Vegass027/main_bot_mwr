from pathlib import Path

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

from bot.keyboards.keyboards import (
    get_partner_qualification_menu,
    get_partner_passive_income_button,
    get_partner_travel_free_button,
    get_partner_quit_job_button,
    get_partner_passive_income_final,
    get_partner_travel_free_final,
    get_partner_quit_job_final
)
from bot.services.user_service import UserService
from bot.utils.states import UserStates

router = Router()

PARTNER_QUALIFICATION = """Отличный выбор. Деньги любят масштаб 📊

Туризм — это единственная индустрия, которую не надо "продавать".

Людей не нужно уговаривать поехать в отпуск.

Они мечтают об этом весь год и копят деньги сами.

**Факты:**
🌍 Объем рынка: **$8.8 Триллионов** в год.
📈 Это больше, чем нефть, золото и IT вместе взятые.
💸 Мы зарабатываем % от этого оборота, просто давая людям доступ к оптовым ценам.

Чтобы я показал стратегию старта под твои цели, скажи: **что для тебя сейчас в приоритете?** 👇"""

# ВЕТКА 1: Пассивный доход
PARTNER_PASSIVE_INCOME = """**Без иллюзий. Только факты 📊**

Пассивный доход — это результат построенной системы, а не удачи.

**Как мы это делаем:**
Мы строим сеть абонентов (как мобильная связь). Люди пользуются продуктом (выгодно путешествуют), потому что им это нравится.

**Твоя роль:**
Организовать этот процесс. Не бегать с каталогами, а выстроить **Цифровой актив**.

⚙️ **У меня уже есть готовая Система:**
Я не предлагаю тебе изобретать велосипед. У нас есть пошаговый алгоритм, который приводит к результату, если просто делать 1-2-3.

⏳ Да, придется поработать на старте.
💰 Но результат — это денежный поток, который не зависит от твоего времени.

Я покажу тебе конкретную математику: сколько действий = сколько денег."""

PARTNER_PASSIVE_INCOME_FINAL = """**План выхода на $2000/мес 🚀**

Чтобы не быть голословным, я загрузил всю математику в наше закрытое приложение. Там нет "воды", только рабочие инструменты.

**Что тебя ждет внутри:**

🧮 **Калькулятор Дохода:** Введешь желаемую сумму — он покажет, сколько партнеров для этого нужно.
🤖 **Моя Система:** Увидишь изнутри инструменты, которыми мы строим команду на автомате.
📈 **Стратегия 90 дней:** Пошаговый план, как новичку сделать первый результат.

Переходи, изучи цифры и напиши мне, если готов стартовать."""

# ВЕТКА 2: Путешествовать бесплатно
PARTNER_TRAVEL_FREE = """**Хакни систему: Расходы ➡️ Доходы**

Это звучит как сказка, но это математика.

Отели тратят миллиарды на рекламу. Мы забираем эти бюджеты себе, просто рекомендуя сервис.

**Как работает модель "Free Travel":**

1️⃣ **Ты пользуешься.** Экономишь на отелях сам.
2️⃣ **Ты рекомендуешь.** Показываешь эту выгоду окружению.
3️⃣ **Ты получаешь.** Всего несколько активных рекомендаций полностью перекрывают стоимость твоего членства.

С этого момента компания начинает пополнять твой счет на путешествия **вместо тебя**.

Твой отпуск больше никогда не будет стоить тебе ни копейки из семейного бюджета."""

PARTNER_TRAVEL_FREE_FINAL = """**Магнит вместо рупора 🧲**

Худшее, что можно делать в бизнесе — это уговаривать. Мы работаем иначе.

**Наша стратегия:**
Мы создаем интерес через результаты. Ты показываешь выгоду (цены, примеры) — люди сами спрашивают "Где это?".

**Внутри Бизнес-Системы тебя ждут:**
🎁 **Метод "Дающего":** Как рекомендовать клуб так, чтобы тебе говорили "Спасибо".
📱 **Контент-стратегия:** Примеры постов и сторис, которые генерируют вопросы от друзей.
🚀 **Твой первый шаг:** Простая инструкция, как закрыть квалификацию без звонков и списков.

Забирай эти инструменты. Они работают на тебя 24/7."""

# ВЕТКА 3: Уволиться из найма
PARTNER_QUIT_JOB = """Слушай, я тебя прекрасно понимаю. Уходить в никуда — это огромный стресс, и я точно не буду тебе говорить «бросай всё и беги к нам». Это глупо.

Самый кайф в том, чтобы построить своё дело параллельно. Спокойно, без нервов, уделяя этому час-два вечером.

Просто представь чувство: ты идешь на работу не потому, что боишься, что нечем будет платить за квартиру, а просто потому что пока так решил. А твой доход здесь уже перекрывает твои расходы.

Вот это и есть настоящая свобода — когда у тебя появляется выбор.
Давай покажу, как к этому прийти мягко и безопасно."""

PARTNER_QUIT_JOB_FINAL = """Всё уже готово внутри 📲

Я специально упаковал всё в формат приложения, чтобы ты мог разобраться во всем сам, в удобном темпе, без лишнего шума.

Что там есть:

✅ Изнанка бизнеса: Честно показываю, как мы путешествуем и зарабатываем на этом.
✅ Умные инструменты: Как строить дело современно, не дергая друзей и знакомых.
✅ Стратегия: Простой план, как создать себе "подушку безопасности" параллельно с основной работой.

Дверь открыта. Заходи, осмотрись. Если идея тебе откликнется — буду рад пообщаться лично."""

@router.callback_query(F.data == "partner")
async def partner_qualification(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Квалификация партнера"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    # Если есть реферер, добавляем событие в радар
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Нажал 'Бизнес'"
        )
    
    # Отправляем изображение с текстом
    image_path = Path("Buisness.jpg")
    if image_path.exists():
        photo = FSInputFile(image_path)
        
        try:
            await callback.message.answer_photo(
                photo=photo,
                caption=PARTNER_QUALIFICATION,
                reply_markup=get_partner_qualification_menu(),
                parse_mode="Markdown"
            )
            # Удаляем старое сообщение, если оно было
            try:
                await callback.message.delete()
            except:
                pass  # Если не удалось удалить, не страшно
        except Exception as e:
            # Если не удалось отправить фото, отправляем просто текст
            try:
                await callback.message.edit_text(
                    PARTNER_QUALIFICATION,
                    reply_markup=get_partner_qualification_menu()
                )
            except TelegramBadRequest:
                # Если не можем отредактировать сообщение, отправляем новое
                await callback.message.answer(
                    PARTNER_QUALIFICATION,
                    reply_markup=get_partner_qualification_menu()
                )
    else:
        # Если изображение не найдено, отправляем просто текст
        try:
            await callback.message.edit_text(
                PARTNER_QUALIFICATION,
                reply_markup=get_partner_qualification_menu()
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                # Если сообщение не изменилось, просто отправляем ответ на callback
                await callback.answer("Квалификация партнера", show_alert=False)
            else:
                # Если другая ошибка BadRequest, пробрасываем дальше
                raise
    
    await state.set_state(UserStates.partner_qualification)
    await callback.answer()

# ВЕТКА 1: Пассивный доход
@router.callback_query(F.data == "partner_passive_income")
async def partner_passive_income(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Ветка пассивного дохода - начало"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Выбрал: Пассивный доход"
        )
    
    # Отправляем текст
    try:
        await callback.message.edit_text(PARTNER_PASSIVE_INCOME, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e) or "there is no text in the message to edit" in str(e):
            # Если сообщение не изменилось или нет текста для редактирования, отправляем новое сообщение
            await callback.message.answer(PARTNER_PASSIVE_INCOME, parse_mode="Markdown")
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_passive_income_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_passive_income_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "Ну кайф же, скажи?😎",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📉 Показать схему дохода", callback_data="partner_show_income_scheme")]
        ])
    )
    
    await state.set_state(UserStates.partner_passive_income)
    await callback.answer()

@router.callback_query(F.data == "partner_show_income_scheme")
async def partner_show_income_scheme(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Промежуточный шаг - показать схему дохода и финальное сообщение для ветки Пассивный доход"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Нажал 'Показать схему дохода'"
        )
    
    # Отправляем текст
    try:
        await callback.message.edit_text(PARTNER_PASSIVE_INCOME_FINAL, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Схема дохода", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть финальное голосовое - отправляем
    if referrer and referrer.voice_passive_income_final_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_passive_income_final_id)
    
    # Отправляем кнопки
    await callback.message.answer(
        "Жду тебя в клубе!❤️‍🔥",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Открыть Бизнес-Систему", url="https://clubsmarttravel.vercel.app/?source=business")]
        ])
    )
    
    await state.set_state(UserStates.partner_passive_income_final)
    await callback.answer()

# ВЕТКА 2: Путешествовать бесплатно
@router.callback_query(F.data == "partner_travel_free")
async def partner_travel_free(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Ветка путешествовать бесплатно - начало"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Выбрал: Путешествовать бесплатно"
        )
    
    # Отправляем текст
    try:
        await callback.message.edit_text(PARTNER_TRAVEL_FREE, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e) or "there is no text in the message to edit" in str(e):
            # Если сообщение не изменилось или нет текста для редактирования, отправляем новое сообщение
            await callback.message.answer(PARTNER_TRAVEL_FREE, parse_mode="Markdown")
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_free_travel_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_free_travel_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "А что, так можно было?😂",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✈️ Как начать летать бесплатно?", callback_data="partner_show_travel_how")]
        ])
    )
    
    await state.set_state(UserStates.partner_travel_free)
    await callback.answer()

@router.callback_query(F.data == "partner_show_travel_how")
async def partner_show_travel_how(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Промежуточный шаг - как начать летать бесплатно и финальное сообщение для ветки Путешествовать бесплатно"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Нажал 'Как начать летать бесплатно'"
        )
    
    # Отправляем текст
    try:
        await callback.message.edit_text(PARTNER_TRAVEL_FREE_FINAL, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("Как начать летать бесплатно", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть финальное голосовое - отправляем
    if referrer and referrer.voice_free_travel_final_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_free_travel_final_id)
    
    # Отправляем кнопки
    await callback.message.answer(
        "Жду тебя в клубе!❤️‍🔥",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Открыть Стратегию", url="https://clubsmarttravel.vercel.app/?source=business")]
        ])
    )
    
    await state.set_state(UserStates.partner_travel_free_final)
    await callback.answer()

# ВЕТКА 3: Уволиться из найма
@router.callback_query(F.data == "partner_quit_job")
async def partner_quit_job(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Ветка увольнения - начало"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Выбрал: Уволиться из найма"
        )
    
    # Отправляем текст
    try:
        await callback.message.edit_text(PARTNER_QUIT_JOB, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e) or "there is no text in the message to edit" in str(e):
            # Если сообщение не изменилось или нет текста для редактирования, отправляем новое сообщение
            await callback.message.answer(PARTNER_QUIT_JOB, parse_mode="Markdown")
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_freedom_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_freedom_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "Жизнь До и После. Смотри👇🏻",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧩 Посмотреть стратегию", callback_data="partner_show_quit_plan")]
        ])
    )
    
    await state.set_state(UserStates.partner_quit_job)
    await callback.answer()

@router.callback_query(F.data == "partner_show_quit_plan")
async def partner_show_quit_plan(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Промежуточный шаг - план побега из найма и финальное сообщение для ветки Уволиться из найма"""
    
    telegram_id = str(callback.from_user.id)
    user = await UserService.get_user_by_telegram_id(session, telegram_id)
    
    if user.referred_by_user_id:
        await UserService.add_radar_event(
            session=session,
            partner_id=user.referred_by_user_id,
            lead_id=user.id,
            action_type="Нажал 'План побега из найма'"
        )
    
    # Отправляем текст
    try:
        await callback.message.edit_text(PARTNER_QUIT_JOB_FINAL, parse_mode="Markdown")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто отправляем ответ на callback
            await callback.answer("План побега из найма", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть финальное голосовое - отправляем
    if referrer and referrer.voice_quit_job_final_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_quit_job_final_id)
    
    # Отправляем кнопки
    await callback.message.answer(
        "Жду тебя в нашем клубе!❤️‍🔥",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Открыть Систему", url="https://clubsmarttravel.vercel.app/?source=business")]
        ])
    )
    
    await state.set_state(UserStates.partner_quit_job_final)
    await callback.answer()