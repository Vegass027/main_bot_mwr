import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from bot.services.user_service import UserService

# ID администратора
ADMIN_ID = 7295309649

logger = logging.getLogger(__name__)

router = Router()
# Этот фильтр будет проверять, что команды в этом роутере
# может использовать только администратор
router.message.filter(F.from_user.id == ADMIN_ID)


@router.message(Command("setpro"))
async def set_pro_status(message: Message, session: AsyncSession):
    """
    Устанавливает статус подписки для пользователя.
    Использование: /setpro <telegram_id> <status>
    Пример: /setpro 123456789 PRO
    """
    # Разбираем команду
    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "Неверный формат команды. Используйте:\n"
            "/setpro <telegram_id> <status>"
        )
        return

    _, target_user_id, new_status = args
    new_status = new_status.upper() # Приводим статус к верхнему регистру

    # Проверяем, существует ли пользователь
    target_user = await UserService.get_user_by_telegram_id(session, target_user_id)
    if not target_user:
        await message.answer(f"Пользователь с ID `{target_user_id}` не найден.")
        return

    # Обновляем статус
    try:
        await UserService.update_subscription_status(
            session=session,
            telegram_id=target_user_id,
            new_status=new_status
        )
        logger.info(f"Admin {message.from_user.id} updated status for {target_user_id} to {new_status}")
        await message.answer(
            f"✅ Статус для пользователя `{target_user_id}` успешно обновлен на `{new_status}`."
        )
    except Exception as e:
        logger.error(f"Failed to update status for {target_user_id}: {e}")
        await message.answer(
            f"❌ Не удалось обновить статус для пользователя `{target_user_id}`. Ошибка: {e}"
        )