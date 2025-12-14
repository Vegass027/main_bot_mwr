"""
Сервис для работы с идеями контента
Следует принципам из RULEZ.md: один запрос = одна транзакция
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ContentIdea, ContentType

logger = logging.getLogger(__name__)


class ContentIdeasService:
    """Сервис для работы с идеями контента"""
    
    @staticmethod
    async def create_idea(
        session: AsyncSession,
        user_id: UUID,
        title: str,
        description: Optional[str] = None,
        content_type_id: Optional[int] = None,
        platform: Optional[str] = None,
        is_saved: bool = False
    ) -> ContentIdea:
        """
        Создать новую идею
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
            title: Название идеи
            description: Описание идеи
            content_type_id: ID типа контента
            platform: Платформа (telegram/instagram/threads)
            is_saved: Сохранена ли идея в планер
        
        Returns:
            ContentIdea: Созданная идея
        """
        try:
            idea = ContentIdea(
                user_id=user_id,
                title=title,
                description=description,
                content_type_id=content_type_id,
                platform=platform,
                is_saved=is_saved,
                is_archived=False
            )
            
            session.add(idea)
            await session.flush()
            
            logger.info(f"Создана идея для user_id={user_id}, idea_id={idea.id}")
            
            return idea
            
        except Exception as e:
            logger.error(f"Ошибка при создании идеи: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_idea(session: AsyncSession, idea_id: UUID) -> Optional[ContentIdea]:
        """
        Получить идею по ID
        
        Args:
            session: Async сессия БД
            idea_id: ID идеи
        
        Returns:
            ContentIdea или None
        """
        try:
            result = await session.execute(
                select(ContentIdea)
                .where(ContentIdea.id == idea_id)
            )
            
            idea = result.scalar_one_or_none()
            
            return idea
            
        except Exception as e:
            logger.error(f"Ошибка при получении идеи: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_idea_by_id(session: AsyncSession, idea_id: UUID) -> Optional[ContentIdea]:
        """
        Получить идею по ID с подгрузкой связанных данных
        
        Args:
            session: Async сессия БД
            idea_id: ID идеи
        
        Returns:
            ContentIdea или None
        """
        try:
            from sqlalchemy.orm import selectinload
            
            result = await session.execute(
                select(ContentIdea)
                .options(selectinload(ContentIdea.content_type))
                .where(ContentIdea.id == idea_id)
            )
            
            idea = result.scalar_one_or_none()
            
            return idea
            
        except Exception as e:
            logger.error(f"Ошибка при получении идеи по ID: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_saved_ideas(
        session: AsyncSession,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ContentIdea]:
        """
        Получить сохраненные идеи пользователя (планер)
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
            limit: Лимит записей
            offset: Смещение для пагинации
        
        Returns:
            List[ContentIdea]: Список сохраненных идей
        """
        try:
            result = await session.execute(
                select(ContentIdea)
                .where(
                    and_(
                        ContentIdea.user_id == user_id,
                        ContentIdea.is_saved == True,
                        ContentIdea.is_archived == False
                    )
                )
                .order_by(ContentIdea.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            ideas = result.scalars().all()
            
            logger.debug(f"Получено {len(ideas)} сохраненных идей для user_id={user_id}")
            
            return list(ideas)
            
        except Exception as e:
            logger.error(f"Ошибка при получении сохраненных идей: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def save_idea(session: AsyncSession, idea_id: UUID) -> bool:
        """
        Сохранить идею в планер
        
        Args:
            session: Async сессия БД
            idea_id: ID идеи
        
        Returns:
            bool: True если успешно сохранено
        """
        try:
            await session.execute(
                update(ContentIdea)
                .where(ContentIdea.id == idea_id)
                .values(is_saved=True)
            )
            
            await session.flush()
            
            logger.info(f"Идея сохранена в планер: idea_id={idea_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении идеи: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def archive_idea(session: AsyncSession, idea_id: UUID) -> bool:
        """
        Архивировать идею (удаление из планера)
        
        Args:
            session: Async сессия БД
            idea_id: ID идеи
        
        Returns:
            bool: True если успешно архивировано
        """
        try:
            await session.execute(
                update(ContentIdea)
                .where(ContentIdea.id == idea_id)
                .values(is_archived=True)
            )
            
            await session.flush()
            
            logger.info(f"Идея архивирована: idea_id={idea_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при архивировании идеи: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_content_types(session: AsyncSession) -> List[ContentType]:
        """
        Получить все типы контента
        
        Args:
            session: Async сессия БД
        
        Returns:
            List[ContentType]: Список типов контента
        """
        try:
            result = await session.execute(
                select(ContentType)
                .order_by(ContentType.id.asc())
            )
            
            content_types = result.scalars().all()
            
            logger.debug(f"Получено {len(content_types)} типов контента")
            
            return list(content_types)
            
        except Exception as e:
            logger.error(f"Ошибка при получении типов контента: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_content_type_by_id(session: AsyncSession, type_id: int) -> Optional[ContentType]:
        """
        Получить тип контента по ID
        
        Args:
            session: Async сессия БД
            type_id: ID типа контента
        
        Returns:
            ContentType или None
        """
        try:
            result = await session.execute(
                select(ContentType)
                .where(ContentType.id == type_id)
            )
            
            content_type = result.scalar_one_or_none()
            
            return content_type
            
        except Exception as e:
            logger.error(f"Ошибка при получении типа контента: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_ideas_grouped_by_type(
        session: AsyncSession,
        user_id: UUID
    ) -> Dict[int, int]:
        """
        Получить группировку сохраненных идей по типам контента с подсчетом
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
        
        Returns:
            Dict[int, int]: Словарь {content_type_id: количество_идей}
        """
        try:
            result = await session.execute(
                select(ContentIdea.content_type_id)
                .where(
                    and_(
                        ContentIdea.user_id == user_id,
                        ContentIdea.is_saved == True,
                        ContentIdea.is_archived == False,
                        ContentIdea.content_type_id.isnot(None)
                    )
                )
            )
            
            ideas = result.scalars().all()
            
            # Группируем и считаем
            grouped = {}
            for type_id in ideas:
                grouped[type_id] = grouped.get(type_id, 0) + 1
            
            logger.debug(f"Группировка идей для user_id={user_id}: {grouped}")
            
            return grouped
            
        except Exception as e:
            logger.error(f"Ошибка при группировке идей: {e}", exc_info=True)
            return {}
    
    @staticmethod
    async def get_saved_ideas_by_type(
        session: AsyncSession,
        user_id: UUID,
        content_type_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[ContentIdea]:
        """
        Получить сохраненные идеи пользователя по типу контента
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
            content_type_id: ID типа контента
            limit: Лимит записей
            offset: Смещение для пагинации
        
        Returns:
            List[ContentIdea]: Список сохраненных идей этого типа
        """
        try:
            result = await session.execute(
                select(ContentIdea)
                .where(
                    and_(
                        ContentIdea.user_id == user_id,
                        ContentIdea.is_saved == True,
                        ContentIdea.is_archived == False,
                        ContentIdea.content_type_id == content_type_id
                    )
                )
                .order_by(ContentIdea.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            ideas = result.scalars().all()
            
            logger.debug(f"Получено {len(ideas)} идей типа {content_type_id} для user_id={user_id}")
            
            return list(ideas)
            
        except Exception as e:
            logger.error(f"Ошибка при получении идей по типу: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def count_saved_ideas(session: AsyncSession, user_id: UUID) -> int:
        """
        Подсчитать количество сохраненных идей пользователя
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
        
        Returns:
            int: Количество идей
        """
        try:
            result = await session.execute(
                select(ContentIdea)
                .where(
                    and_(
                        ContentIdea.user_id == user_id,
                        ContentIdea.is_saved == True,
                        ContentIdea.is_archived == False
                    )
                )
            )
            
            count = len(result.scalars().all())
            
            return count
            
        except Exception as e:
            logger.error(f"Ошибка при подсчете идей: {e}", exc_info=True)
            return 0