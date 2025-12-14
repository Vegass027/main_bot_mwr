"""
Performance Monitoring Middleware.

Отслеживает время выполнения хендлеров и логирует медленные операции.
"""

import time
import logging
from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)

# Порог для "медленных" операций (в секундах)
SLOW_OPERATION_THRESHOLD = 0.5  # 500ms

class PerformanceMiddleware(BaseMiddleware):
    """
    Middleware для измерения производительности хендлеров.
    
    Логирует:
    - Время выполнения каждого хендлера
    - Медленные операции (> 500ms)
    - Ошибки с временем выполнения
    """
    
    def _get_event_description(self, event: TelegramObject) -> str:
        """Получить читаемое описание события"""
        
        if isinstance(event, CallbackQuery):
            callback_data = event.data[:30] if event.data else "No data"
            return f"CallbackQuery({callback_data})"
        
        if isinstance(event, Message):
            # Если есть текст, показываем его
            if event.text:
                text_preview = event.text[:30]
                return f"Message(text: {text_preview})"
            # Если фото, показываем с подписью или без
            elif event.photo:
                caption = f", caption: {event.caption[:20]}" if event.caption else ""
                return f"Message(photo{caption})"
            # Другие типы контента
            elif event.voice:
                return "Message(voice)"
            elif event.document:
                return "Message(document)"
            elif event.sticker:
                return "Message(sticker)"
            
            return "Message(Unknown Content)"
            
        return type(event).__name__
    
    def _get_user_id(self, event: TelegramObject) -> Optional[int]:
        """Получить ID пользователя из события"""
        if hasattr(event, 'from_user') and event.from_user:
            return event.from_user.id
        elif hasattr(event, 'message') and event.message and hasattr(event.message, 'from_user'):
            return event.message.from_user.id
        return None
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        user_id = self._get_user_id(event)
        
        # Защита от падения при описании события
        try:
            event_desc = self._get_event_description(event)
        except Exception:
            event_desc = "UnknownEvent(Error in description)"
        
        try:
            # Выполняем хендлер
            result = await handler(event, data)
            
            # Измеряем время
            duration = time.time() - start_time
            
            # Логируем медленные операции
            if duration > SLOW_OPERATION_THRESHOLD:
                logger.warning(
                    f"SLOW OPERATION: {event_desc}",
                    extra={
                        "event_description": event_desc,
                        "user_id": user_id,
                        "duration_ms": round(duration * 1000, 2),
                        "handler": handler.__name__ if hasattr(handler, '__name__') else str(handler)
                    }
                )
            else:
                # Логируем обычные операции на уровне DEBUG
                logger.debug(
                    f"Handler executed: {event_desc}",
                    extra={
                        "event_description": event_desc,
                        "user_id": user_id,
                        "duration_ms": round(duration * 1000, 2),
                        "handler": handler.__name__ if hasattr(handler, '__name__') else str(handler)
                    }
                )
            
            return result
            
        except Exception as e:
            # Логируем ошибки с временем выполнения
            duration = time.time() - start_time
            
            logger.error(
                f"Handler failed: {event_desc}",
                exc_info=True,
                extra={
                    "event_description": event_desc,
                    "user_id": user_id,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e)
                }
            )
            
            # Пробрасываем исключение дальше
            raise
