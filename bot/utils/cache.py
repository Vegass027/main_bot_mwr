"""
Простая система кэширования для часто используемых данных.

Использует in-memory кэш с TTL для:
- Opponent profiles
- User profiles (опционально)
- Knowledge base queries
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Простой in-memory кэш с поддержкой TTL (Time To Live).
    
    Правила:
    - Данные хранятся в памяти
    - Автоматическое истечение по TTL
    - Потокобезопасен для async/await
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Args:
            default_ttl: Время жизни кэша в секундах (по умолчанию 1 час)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Сохранить значение в кэш.
        
        Args:
            key: Уникальный ключ
            value: Значение для кэширования
            ttl: Время жизни в секундах (опционально)
        """
        expires_at = datetime.now() + timedelta(seconds=ttl or self._default_ttl)
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
        
        logger.debug(f"Cache SET: {key} (TTL: {ttl or self._default_ttl}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кэша.
        
        Args:
            key: Ключ для поиска
            
        Returns:
            Значение или None если не найдено/истекло
        """
        if key not in self._cache:
            logger.debug(f"Cache MISS: {key}")
            return None
        
        entry = self._cache[key]
        
        # Проверяем TTL
        if datetime.now() > entry['expires_at']:
            # Удаляем истекшую запись
            del self._cache[key]
            logger.debug(f"Cache EXPIRED: {key}")
            return None
        
        logger.debug(f"Cache HIT: {key}")
        return entry['value']
    
    def delete(self, key: str) -> bool:
        """
        Удалить значение из кэша.
        
        Args:
            key: Ключ для удаления
            
        Returns:
            True если удалено, False если не найдено
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache DELETE: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """Очистить весь кэш"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache CLEARED: {count} items removed")
    
    def cleanup_expired(self) -> int:
        """
        Удалить все истекшие записи.
        
        Returns:
            Количество удаленных записей
        """
        now = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now > entry['expires_at']
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cache CLEANUP: {len(expired_keys)} expired items removed")
        
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """
        Получить статистику кэша.
        
        Returns:
            Словарь со статистикой
        """
        now = datetime.now()
        active_count = sum(
            1 for entry in self._cache.values()
            if now <= entry['expires_at']
        )
        expired_count = len(self._cache) - active_count
        
        return {
            'total_items': len(self._cache),
            'active_items': active_count,
            'expired_items': expired_count
        }


# Глобальный кэш для opponent profiles
# TTL = 1 час (профили соперников редко меняются)
opponent_cache = SimpleCache(default_ttl=3600)

# Глобальный кэш для knowledge base queries
# TTL = 30 минут
knowledge_cache = SimpleCache(default_ttl=1800)