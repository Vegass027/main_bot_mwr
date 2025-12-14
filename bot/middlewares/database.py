from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.database.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для управления транзакциями и инъекции сессии БД в хендлеры.
    
    Правила:
    - Одна сессия на один запрос/хендлер
    - Автоматический commit при успехе
    - Автоматический rollback при ошибке
    - Сервисы НЕ должны делать commit/rollback сами
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data['session'] = session
            
            try:
                # Выполняем хендлер
                result = await handler(event, data)
                
                # Коммитим транзакцию при успехе
                await session.commit()
                
                return result
                
            except Exception as e:
                # Откатываем транзакцию при ошибке
                await session.rollback()
                
                # Логируем ошибку с контекстом
                logger.error(
                    "Database transaction failed",
                    exc_info=True,
                    extra={
                        "event_type": type(event).__name__,
                        "error": str(e)
                    }
                )
                
                # Пробрасываем исключение дальше
                raise