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
from bot.services.llm_service import get_llm_service

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
                has_pay_less_voice=bool(user.voice_pay_less_id),
                has_5star_3star_voice=bool(user.voice_5star_3star_id),
                has_travel_more_voice=bool(user.voice_travel_more_id),
                has_passive_income_voice=bool(user.voice_passive_income_id),
                has_passive_income_final_voice=bool(user.voice_passive_income_final_id),
                has_free_travel_voice=bool(user.voice_free_travel_id),
                has_free_travel_final_voice=bool(user.voice_free_travel_final_id),
                has_quit_job_voice=bool(user.voice_freedom_id),
                has_quit_job_final_voice=bool(user.voice_quit_job_final_id)
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
    
    prompt_text = '''📹 **Приветствие (Видео-кружок)**

Запиши Видео-сообщение (Кружочек).
Это первое, что увидит человек 
после нажатия "Старт".

📝 **Сценарий:**

🎭 **Актерские рекомендации 
(чтобы было "человечно"):**

1. **Начало:** Можно поправить волосы 
или просто улыбнуться в камеру **ДО** того, 
как начнешь говорить. Это создает эффект 
живого общения.
    
2. **Слова-паразиты (специальные):** 
Слова "Слушай", "Короче", "Честно" — 
делают речь живой. Не нужно говорить 
как диктор новостей.
    
3. **Интонация:** Не тараторить. 
Говорить спокойно. Представь, что 
записываешь это другу, с которым 
вчера пил кофе.

**Вариант 1: "Свой в доску"**

"Привет! Слушай, рад, что ты зашел.

Чтобы я тебе сейчас полотна текста 
не писал и время не тратил, давай 
проще поступим.

У меня здесь две темы. Первая — это 
как мы находим отели и туры реально 
в 2 раза дешевле, чем все остальные. 
А вторая — как на этой всей истории 
деньги делаются.

Тебе честно сейчас что интереснее — 
просто выгодно в отпуск сгонять или 
доход построить?

Ткни кнопку внизу, я тебе именно 
про это и расскажу."

**Вариант 2: "На энергии" 
(Эмоциональный, искренний)**

"Привет! Класс, что ты здесь.

Скажу честно — то, что я тут показываю, 
меня самого очень сильно зацепило. 
Потому что здесь можно жить в 
лакшери-отелях по цене обычной «трешки», 
ну или вообще сделать путешествия 
своим бизнесом.

Я не знаю, ты больше про «отдохнуть» 
или про «движ и деньги», поэтому 
не хочу тебя грузить лишним.

Выбери внизу свой вариант, и погнали!"

⏳ **Жду твой кружочек...**'''
    
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
    
    prompt_text = """💸 **Ветка: 📉 Платить меньше**

Запиши Голосовое сообщение для тех, кто выбрал 'Платить меньше'.
Бот отправит его в ветке "Путешествия".

📝 **Сценарий:**

> _"Слушай, тут всё на самом деле просто. Отели — это скоропортящийся продукт. Если номер сегодня ночью пустой, отель потерял деньги навсегда._
>
> _Поэтому они готовы отдавать эти номера закрытым клубам, типа нашего, со скидкой 50-70%, лишь бы заполнить._
>
> _Но они запрещают показывать эти цены публично на Букинге или Островке, чтобы не рушить рынок. А нам внутри клуба — можно. Вот и весь секрет. Ты просто получаешь доступ к оптовым ценам, которые скрыты от обычных туристов."_

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
    
    prompt_text = """🌍 **Ветка: 👑 Жить в 5★ по цене 3★**

Запиши Голосовое сообщение для тех, кто выбрал 'Жить в 5★ по цене 3★'.
Бот отправит его в ветке "Путешествия".

📝 **Сценарий:**
_"Слушай, я раньше всегда думал: ну нафига переплачивать за отель, я ж там только сплю? А потом понял, что я так говорил, просто потому что денег жалел._
 
_А тут фишка в чем... Ты можешь за те же самые деньги — вот реально за те же, что планировал потратить на обычный отель — взять уровень на голову выше._
 
_Ну то есть, вместо обычной гостиницы — взять крутой отель с бассейном на крыше или со своим пляжем. Бюджет тот же, а впечатления вообще другие. Вот это для меня самое ценное здесь."_

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
    await state.set_state(UserStates.awaiting_travel_more_voice)
    await callback.answer()

@router.message(UserStates.awaiting_travel_more_voice, F.voice)
async def save_travel_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение голосового для ветки Путешествия"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_travel_more(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Голосовое для ветки 'Путешествия' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_travel_more_voice)
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

# Обработчик ветки "Платить меньше" (голосовое)
@router.callback_query(F.data == "upload_pay_less_voice")
async def upload_pay_less_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку голосового для ветки Платить меньше"""
    
    prompt_text = """📉 **Ветка: Платить меньше**

Запиши Голосовое сообщение для тех, кто выбрал 'Платить меньше'.
Бот отправит его в ветке "Путешествия".

📝 **Сценарий:**
_"Слушай, тут всё на самом деле просто. Отели — это скоропортящийся продукт. Если номер сегодня ночью пустой, отель потерял деньги навсегда._

_Поэтому они готовы отдавать эти номера закрытым клубам, типа нашего, со скидкой 50-70%, лишь бы заполнить._

_Но они запрещают показывать эти цены публично на Букинге или Островке, чтобы не рушить рынок. А нам внутри клуба — можно. Вот и весь секрет. Ты просто получаешь доступ к оптовым ценам, которые скрыты от обычных туристов."_

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
            await callback.answer("Запись 'Платить меньше'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_pay_less_voice)
    await callback.answer()

@router.message(UserStates.awaiting_pay_less_voice, F.voice)
async def save_pay_less_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение голосового для ветки Платить меньше"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_pay_less(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Голосовое для ветки 'Платить меньше' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_pay_less_voice)
async def wrong_pay_less_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик ветки "Жить в 5★ по цене 3★" (голосовое)
@router.callback_query(F.data == "upload_5star_3star_voice")
async def upload_5star_3star_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку голосового для ветки Жить в 5★ по цене 3★"""
    
    prompt_text = """👑 **Ветка: Жить в 5★ по цене 3★**

Запиши Голосовое сообщение для тех, кто выбрал 'Жить в 5★ по цене 3★'.
Бот отправит его в ветке "Путешествия".

📝 **Сценарий:**
_"Слушай, я раньше всегда думал: ну нафига переплачивать за отель, я ж там только сплю? А потом понял, что я так говорил, просто потому что денег жалел._
 
_А тут фишка в чем... Ты можешь за те же самые деньги — вот реально за те же, что планировал потратить на обычный отель — взять уровень на голову выше._
 
_Ну то есть, вместо обычной гостиницы — взять крутой отель с бассейном на крыше или со своим пляжем. Бюджет тот же, а впечатления вообще другие. Вот это для меня самое ценное здесь."_

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
            await callback.answer("Запись 'Жить в 5★ по цене 3★'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_5star_3star_voice)
    await callback.answer()

@router.message(UserStates.awaiting_5star_3star_voice, F.voice)
async def save_5star_3star_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение голосового для ветки Жить в 5★ по цене 3★"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_5star_3star(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Голосовое для ветки 'Жить в 5★ по цене 3★' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_5star_3star_voice)
async def wrong_5star_3star_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик ветки "Путешествовать чаще" (голосовое)
@router.callback_query(F.data == "upload_travel_more_voice")
async def upload_travel_more_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку голосового для ветки Путешествовать чаще"""
    
    prompt_text = """🌍 **Ветка: Путешествовать чаще**

Запиши Голосовое сообщение для тех, кто выбрал 'Путешествовать чаще'.
Бот отправит его в ветке "Путешествия".

📝 **Сценарий:**
_"Слушай, мы все хотим путешествовать чаще, но вечно откладываем это «на потом». Всегда находятся дела поважнее, куда потратить деньги._

_А здесь система построена так, что ты по чуть-чуть откладываешь себе на счет — как подписка. Только эти деньги не сгорают, они копятся._

_И в какой-то момент ты заходишь в приложение и видишь: о, у меня уже на целый отпуск собралось!_

_И ты просто берешь и летишь. Не потому что надо напрягаться и искать деньги, а потому что они уже там. Это реально самый простой способ начать ездить куда-то 3-4 раза в год."_

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
            await callback.answer("Запись 'Путешествовать чаще'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_travel_more_voice)
    await callback.answer()

@router.message(UserStates.awaiting_travel_more_voice, F.voice)
async def save_travel_more_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение голосового для ветки Путешествовать чаще"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_travel_more(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Голосовое для ветки 'Путешествовать чаще' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_travel_more_voice)
async def wrong_travel_more_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик финального призыва ветки "Пассивный доход" (голосовое)
@router.callback_query(F.data == "upload_passive_income_final_voice")
async def upload_passive_income_final_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку финального голосового для ветки Пассивный доход"""
    
    prompt_text = """🏁 **Финал ветки: 💸 Пассивный доход**

Запиши Голосовое сообщение для финала ветки "Пассивный доход".
Бот отправит его перед кнопкой входа в Приложение (Бизнес Хаб).

📝 **Сценарий:**
_"Короче, я не хочу тебе тут расписывать поэмы. Деньги любят счет._

_Я подготовил для тебя доступ в наше приложение. Там есть всё: калькулятор, моя система, конкретные цифры. Зайди, потыкай кнопки, посчитай сам свою выгоду._

_Если увидишь в этом перспективу — там внутри есть мои контакты. Напиши, обсудим стратегию. Жду тебя внутри."_

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
            await callback.answer("Запись финала 'Пассивный доход'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_passive_income_final_voice)
    await callback.answer()

@router.message(UserStates.awaiting_passive_income_final_voice, F.voice)
async def save_passive_income_final_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение финального голосового для ветки Пассивный доход"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_passive_income_final(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Финальное голосовое для ветки 'Пассивный доход' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_passive_income_final_voice)
async def wrong_passive_income_final_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик ветки "Путешествовать бесплатно" (голосовое)
@router.callback_query(F.data == "upload_free_travel_voice")
async def upload_free_travel_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку голосового для ветки Путешествовать бесплатно"""
    
    prompt_text = """🌍 **Ветка: Путешествовать бесплатно**

Запиши Голосовое сообщение для тех, кто выбрал 'Путешествовать бесплатно'.
Бот отправит его в ветке "Бизнес".

📝 **Сценарий:**
_"Слушай, самая гениальная вещь здесь — это то, что ты можешь вообще убрать из своего бюджета расходы на отпуск._

_Мы все тратим на это кучу денег каждый год. А тут компания говорит: «Пользуйся сам, расскажи друзьям, и если они тоже начнут экономить — мы будем оплачивать твои путешествия за тебя»._

_Ты просто вдумайся. Ты не продаешь им пылесосы, ты даешь им способ экономить. И за это компания начинает пополнять твой счет на путешествия каждый месяц. Бесплатно. Я когда понял эту математику, я вообще перестал переживать о ценах на билеты."_

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
            await callback.answer("Запись 'Путешествовать бесплатно'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_free_travel_voice)
    await callback.answer()

@router.message(UserStates.awaiting_free_travel_voice, F.voice)
async def save_free_travel_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение голосового для ветки Путешествовать бесплатно"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_free_travel(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Голосовое для ветки 'Путешествовать бесплатно' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_free_travel_voice)
async def wrong_free_travel_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик финального призыва ветки "Путешествовать бесплатно" (голосовое)
@router.callback_query(F.data == "upload_free_travel_final_voice")
async def upload_free_travel_final_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку финального голосового для ветки Путешествовать бесплатно"""
    
    prompt_text = """🏁 **Финал ветки: 🌍 Путешествовать бесплатно**

Запиши Голосовое сообщение для финала ветки 🌍 Путешествовать бесплатно.
Бот отправит его перед кнопкой входа в Приложение.

📝 **Сценарий:**

"Смотри, чтобы у тебя не было ощущения, что надо за кем-то бегать. Это не работает.

Весь секрет в том, что мы просто показываем людям, как они могут сэкономить свои же деньги. Мы не просим у них денег, мы даем им выгоду. А когда ты даешь человеку выгоду — тебе не надо его «искать» или уговаривать, он сам хочет.

В приложении я показал именно этот подход: как сделать так, чтобы твое окружение само интересовалось, откуда у тебя такие цены. Зайди, посмотри эту стратегию. Это про достоинство, а не про впаривание."

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
            await callback.answer("Запись финала 'Путешествовать бесплатно'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_free_travel_final_voice)
    await callback.answer()

@router.message(UserStates.awaiting_free_travel_final_voice, F.voice)
async def save_free_travel_final_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение финального голосового для ветки Путешествовать бесплатно"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_free_travel_final(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Финальное голосовое для ветки 'Путешествовать бесплатно' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_free_travel_final_voice)
async def wrong_free_travel_final_voice_type(message: Message):
    """Обработка неверного типа контента"""
    
    await message.answer(
        "❌ Пожалуйста, отправь **голосовое сообщение**.",
        parse_mode="Markdown"
    )

# Обработчик финального призыва ветки "Уволиться из найма" (голосовое)
@router.callback_query(F.data == "upload_quit_job_final_voice")
async def upload_quit_job_final_voice_prompt(callback: CallbackQuery, state: FSMContext):
    """Запрос на загрузку финального голосового для ветки Уволиться из найма"""
    
    prompt_text = """🏁 **Финал ветки: 🚀 Уволиться из найма**

Запиши Голосовое сообщение для финала ветки "Уволиться из найма".
Бот отправит его перед кнопкой входа в Приложение (Бизнес Хаб).

📝 **Сценарий:**
_"Смотри, я не хочу грузить тебя теорией. Лучше один раз увидеть._

_Я открыл тебе доступ в наше приложение. Там ты увидишь, как работает наша система изнутри. Не на словах, а на деле — какие инструменты мы используем и почему этот механизм работает так надежно._

_Зайди, спокойно всё изучи, «примерь» на себя. Если почувствуешь, что тебе эта модель откликается — напиши мне, я подскажу, с чего начать."_

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
            await callback.answer("Запись финала 'Уволиться из найма'", show_alert=False)
        else:
            # Если другая ошибка BadRequest, пробрасываем дальше
            raise
    await state.set_state(UserStates.awaiting_quit_job_final_voice)
    await callback.answer()

@router.message(UserStates.awaiting_quit_job_final_voice, F.voice)
async def save_quit_job_final_voice(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранение финального голосового для ветки Уволиться из найма"""
    
    telegram_id = str(message.from_user.id)
    voice_id = message.voice.file_id
    
    await UserService.update_voice_quit_job_final(session, telegram_id, voice_id)
    
    await message.answer_voice(voice=voice_id)
    await message.answer(
        "✅ **Готово! Финальное голосовое для ветки 'Уволиться из найма' сохранено.**",
        reply_markup=get_back_to_personalization(),
        parse_mode="Markdown"
    )
    
    await state.set_state(UserStates.pro_menu)

@router.message(UserStates.awaiting_quit_job_final_voice)
async def wrong_quit_job_final_voice_type(message: Message):
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