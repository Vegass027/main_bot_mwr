import asyncio
import logging
import signal
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
import os

from bot.handlers import admin_handler, start_handler, tourist_handler, partner_handler, pro_handler, ai_designer_handler, ai_trainer_handler, content_maker_handler
from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.performance import PerformanceMiddleware
from bot.database.database import init_db, engine
from bot.utils.http_client import HTTPClientManager

# Загрузка переменных окружения
load_dotenv()

# Настройка улучшенного логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Уменьшаем verbosity сторонних библиотек
logging.getLogger('aiogram').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

async def shutdown(bot: Bot):
    """
    Graceful shutdown - корректное закрытие всех ресурсов.
    """
    logger.info("Начинаем graceful shutdown...")
    
    try:
        # Закрываем HTTP clients
        await HTTPClientManager.close_all()
        logger.info("HTTP clients закрыты")
        
        # Закрываем bot session
        await bot.session.close()
        logger.info("Bot session закрыт")
        
        # Закрываем database engine
        await engine.dispose()
        logger.info("Database engine закрыт")
        
    except Exception as e:
        logger.error(f"Ошибка при shutdown: {e}", exc_info=True)
    
    logger.info("Graceful shutdown завершен")


async def main():
    """
    Главная функция запуска бота с поддержкой graceful shutdown.
    """
    
    # Получаем токен бота
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    # Создаем хранилище для FSM
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключаем middleware в правильном порядке через update.outer_middleware:
    # 1. Performance (измеряет всё)
    # 2. Database (управляет транзакциями)
    # Используем outer_middleware чтобы избежать дублирования обработки
    dp.update.outer_middleware(PerformanceMiddleware())
    dp.update.outer_middleware(DatabaseMiddleware())
    
    # Регистрируем роутеры
    dp.include_router(admin_handler.router)  # Админ-панель
    dp.include_router(start_handler.router)
    dp.include_router(tourist_handler.router)
    dp.include_router(partner_handler.router)
    dp.include_router(pro_handler.router)
    dp.include_router(ai_designer_handler.router)
    dp.include_router(ai_trainer_handler.router)
    dp.include_router(content_maker_handler.router)
    
    # Инициализация БД
    await init_db()
    
    logger.info("🚀 Бот запущен и готов к работе!")
    logger.info(f"📊 Performance monitoring активирован (порог: 500ms)")
    logger.info(f"💾 Database connection pool настроен (size: 10, max_overflow: 20)")
    
    # Запуск polling
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            handle_signals=False  # Обрабатываем сигналы сами
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки")
    finally:
        await shutdown(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)