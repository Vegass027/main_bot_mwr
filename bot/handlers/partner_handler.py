from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

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

PARTNER_QUALIFICATION = """Супер. В туризме крутятся самые большие деньги.

Чтобы я предложил тебе правильный план старта, скажи:

Что для тебя сейчас важнее всего? 👇"""

# ВЕТКА 1: Пассивный доход
PARTNER_PASSIVE_INCOME = """Мудрый выбор. Настоящий пассивный доход — это когда ты получаешь процент от того, на что люди сами хотят тратить деньги.

Никого не надо уговаривать ехать в отпуск. Люди копят на это весь год.

📊 ФАКТ: Рынок туризма — $8.8 ТРИЛЛИОНОВ.
Представь: пока ты спишь, кто-то бронирует отель, а тебе капает комиссия. Даже 0.0001% от этого рынка обеспечат тебя и твоих внуков."""

PARTNER_PASSIVE_INCOME_FINAL = """Главный вопрос инвестора: 'Сколько времени это займет?'.

Чтобы создать пассивный доход, тебе не нужно бегать за клиентами. Мы построили Цифровой Конвейер, который делает это за тебя.

Внутри Бизнес Хаба тебя ждут:

📊 Калькулятор Дохода: Посчитаешь, сколько людей нужно для твоих $2000/мес.
🤖 Твой личный AI-агент: (Которого ты сможешь настроить под себя).
📈 Стратегия: Как выйти на доход без звонков друзьям.

Заходи, посмотри на цифры своими глазами."""

# ВЕТКА 2: Путешествовать бесплатно
PARTNER_TRAVEL_FREE = """Лучшая цель! Зачем платить за жизнь мечты, если индустрия может оплачивать её за тебя?

В MWR Life партнеры превращают свои расходы на отпуск в доходы.

📊 ФАКТ: Рынок туризма — $8.8 ТРИЛЛИОНОВ.
Отели тратят миллиарды на рекламу. Мы помогаем им сэкономить эти деньги, а они в благодарность дают нам бесплатные проживания и Travel-баллы."""

PARTNER_TRAVEL_FREE_FINAL = """Звучит как сказка? Понимаю. Поэтому лучше один раз увидеть.

Тебе не нужно быть турагентом. У нас есть платформа Travel Advantage, которая работает как Booking, только деньги за бронирования возвращаются тебе.

Я открыл тебе доступ в Хаб, где ты увидишь:

🏨 Демонстрацию платформы: Реальные цены на отели прямо сейчас.
✈️ Лайфхаки: Как накапливать баллы на бесплатные перелеты.
🎁 Guest Pass: Инструкция, как подарить другу скидку и заработать на этом.

Твое первое бесплатное путешествие начинается здесь."""

# ВЕТКА 3: Уволиться из найма
PARTNER_QUIT_JOB = """Понимаю. Менять 5 дней жизни на 2 выходных — это плохая сделка. Свобода стоит дороже всего.

Чтобы уволиться, тебе не нужна 'вторая работа'. Тебе нужен бизнес, который работает 24/7 без твоего участия.

📊 ФАКТ: Рынок туризма — $8.8 ТРИЛЛИОНОВ.
Эта индустрия никогда не спит. Пока в твоем городе ночь, в Нью-Йорке люди заселяются в отели. Это и есть фундамент твоей свободы."""

PARTNER_QUIT_JOB_FINAL = """Чтобы уволиться, тебе не нужна 'мотивация'. Тебе нужен четкий план действий, который сработает даже у новичка.

Мы убрали хаос и оставили пошаговый алгоритм.

Внутри Бизнес Хаба я подготовил для тебя:

🚀 Быстрый Старт: Что конкретно сделать в первые 7 дней.
🎓 Академия: Обучение от топ-лидеров (без воды).
📱 Настройка Профиля: Как упаковать себя, чтобы люди сами просились в команду.

Система готова. Ключ зажигания у тебя в руках."""

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
    
    await callback.message.edit_text(
        PARTNER_QUALIFICATION,
        reply_markup=get_partner_qualification_menu()
    )
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
    await callback.message.edit_text(PARTNER_PASSIVE_INCOME)
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_passive_income_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_passive_income_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "Будет интересно и выгодно. Обещаю👇",
        reply_markup=get_partner_passive_income_button()
    )
    
    await state.set_state(UserStates.partner_passive_income)
    await callback.answer()

@router.callback_query(F.data == "partner_show_income_scheme")
async def partner_show_income_scheme(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Промежуточный шаг - показать схему дохода"""
    
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
    await callback.message.edit_text(PARTNER_PASSIVE_INCOME_FINAL)
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть финальное голосовое - отправляем
    if referrer and referrer.voice_final_cta_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_final_cta_id)
    
    # Отправляем кнопки
    await callback.message.answer(
        "Жду тебя в клубе!❤️‍🔥",
        reply_markup=get_partner_passive_income_final()
    )
    
    await state.set_state(UserStates.partner_passive_income_final)
    await callback.answer()

# ВЕТКА 2: Путешествовать бесплатно
@router.callback_query(F.data == "partner_travel_free")
async def partner_travel_free(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Ветка путешествий - начало"""
    
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
    await callback.message.edit_text(PARTNER_TRAVEL_FREE)
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_free_travel_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_free_travel_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "Ну кайф же скажи?) Ты уже в одном шаге от того, чтобы путешествовать бесплатно. Нажимай  👇",
        reply_markup=get_partner_travel_free_button()
    )
    
    await state.set_state(UserStates.partner_travel_free)
    await callback.answer()

@router.callback_query(F.data == "partner_show_travel_how")
async def partner_show_travel_how(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Промежуточный шаг - как начать летать бесплатно"""
    
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
    await callback.message.edit_text(PARTNER_TRAVEL_FREE_FINAL)
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть финальное голосовое - отправляем
    if referrer and referrer.voice_final_cta_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_final_cta_id)
    
    # Отправляем кнопки
    await callback.message.answer(
        "Жду тебя в клубе!❤️‍🔥",
        reply_markup=get_partner_travel_free_final()
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
    await callback.message.edit_text(PARTNER_QUIT_JOB)
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть голосовое - отправляем
    if referrer and referrer.voice_freedom_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_freedom_id)
    
    # Отправляем кнопку
    await callback.message.answer(
        "К черту рабство, пора жить той жизнью, о которой ты мечтал! Жми кнопку ниже 👇",
        reply_markup=get_partner_quit_job_button()
    )
    
    await state.set_state(UserStates.partner_quit_job)
    await callback.answer()

@router.callback_query(F.data == "partner_show_quit_plan")
async def partner_show_quit_plan(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Промежуточный шаг - план побега из найма"""
    
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
    await callback.message.edit_text(PARTNER_QUIT_JOB_FINAL)
    
    # Получаем реферера
    referrer = await UserService.get_referrer(session, user)
    
    # Если у реферера есть финальное голосовое - отправляем
    if referrer and referrer.voice_final_cta_id:
        await asyncio.sleep(0.5)
        await callback.message.answer_voice(voice=referrer.voice_final_cta_id)
    
    # Отправляем кнопки
    await callback.message.answer(
        "Жду тебя в нашем клубе!❤️‍🔥",
        reply_markup=get_partner_quit_job_final()
    )
    
    await state.set_state(UserStates.partner_quit_job_final)
    await callback.answer()