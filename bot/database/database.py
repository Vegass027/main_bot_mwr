from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from bot.database.models import Base
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден в .env файле")

# Создаем асинхронный движок с оптимизированным пулингом
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,        # Проверка живых соединений
    pool_size=10,              # Базовый размер пула (увеличен для нагрузки)
    max_overflow=20,           # Максимальное количество дополнительных соединений
    pool_recycle=3600,         # Переиспользовать соединения каждый час
    pool_timeout=30,           # Таймаут ожидания соединения из пула
    connect_args={
        "server_settings": {
            "application_name": "telegram_bot_mwr"
        },
        "command_timeout": 60,  # Таймаут для команд
    }
)

# Создаем фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Инициализация БД (не создаем таблицы, они уже есть в Supabase)"""
    pass

async def get_session() -> AsyncSession:
    """Получить сессию БД"""
    async with AsyncSessionLocal() as session:
        yield session