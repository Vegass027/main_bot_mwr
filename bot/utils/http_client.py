"""
HTTP Client Manager для переиспользования соединений.

Правила:
- Один глобальный ClientSession для каждого API
- SSL context создается один раз
- Настроены таймауты для всех запросов
- Connection pooling для высокой производительности
"""

import aiohttp
import ssl
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """Менеджер HTTP клиентов для переиспользования соединений"""
    
    _openai_session: Optional[aiohttp.ClientSession] = None
    _fal_session: Optional[aiohttp.ClientSession] = None
    _ssl_context: Optional[ssl.SSLContext] = None
    
    @classmethod
    def _get_ssl_context(cls) -> ssl.SSLContext:
        """Получить или создать SSL контекст (переиспользуется)"""
        if cls._ssl_context is None:
            cls._ssl_context = ssl.create_default_context()
            cls._ssl_context.check_hostname = False
            cls._ssl_context.verify_mode = ssl.CERT_NONE
            logger.info("SSL context created and cached")
        return cls._ssl_context
    
    @classmethod
    async def get_openai_session(cls) -> aiohttp.ClientSession:
        """
        Получить shared ClientSession для OpenAI API.
        
        Переиспользует одно соединение для всех запросов к OpenAI.
        """
        if cls._openai_session is None or cls._openai_session.closed:
            api_key = os.getenv("OPEN_AI_API_KEY")
            if not api_key:
                raise ValueError("OPEN_AI_API_KEY не найден в .env")
            
            # Таймауты для стабильности
            timeout = aiohttp.ClientTimeout(
                total=60,      # Общее время на запрос (OpenAI может быть медленным)
                connect=10,    # Время на подключение
                sock_read=30   # Время на чтение ответа
            )
            
            # Connection pooling
            connector = aiohttp.TCPConnector(
                ssl=cls._get_ssl_context(),
                limit=100,              # Максимум 100 одновременных соединений
                limit_per_host=30,      # Максимум 30 на один хост
                ttl_dns_cache=300       # Кэш DNS на 5 минут
            )
            
            cls._openai_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            logger.info("OpenAI ClientSession created and cached")
        
        return cls._openai_session
    
    @classmethod
    async def get_fal_session(cls) -> aiohttp.ClientSession:
        """
        Получить shared ClientSession для Fal.ai API.
        
        Переиспользует одно соединение для всех запросов к Fal.ai.
        """
        if cls._fal_session is None or cls._fal_session.closed:
            api_key = os.getenv("FAL_AI_API_KEY")
            if not api_key:
                raise ValueError("FAL_AI_API_KEY не найден в .env")
            
            # Таймауты (Fal.ai может генерировать долго)
            timeout = aiohttp.ClientTimeout(
                total=120,     # 2 минуты на генерацию изображения
                connect=10,
                sock_read=60
            )
            
            # Connection pooling
            connector = aiohttp.TCPConnector(
                ssl=cls._get_ssl_context(),
                limit=50,
                limit_per_host=20,
                ttl_dns_cache=300
            )
            
            cls._fal_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "Authorization": f"Key {api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            logger.info("Fal.ai ClientSession created and cached")
        
        return cls._fal_session
    
    @classmethod
    async def close_all(cls):
        """Закрыть все активные сессии (для graceful shutdown)"""
        if cls._openai_session and not cls._openai_session.closed:
            await cls._openai_session.close()
            logger.info("OpenAI ClientSession closed")
        
        if cls._fal_session and not cls._fal_session.closed:
            await cls._fal_session.close()
            logger.info("Fal.ai ClientSession closed")