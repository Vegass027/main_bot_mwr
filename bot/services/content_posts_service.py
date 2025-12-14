"""
Сервис для работы с постами контента
Следует принципам из RULEZ.md: один запрос = одна транзакция
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ContentPost

logger = logging.getLogger(__name__)


class ContentPostsService:
    """Сервис для работы с постами контента"""
    
    @staticmethod
    async def create_post(
        session: AsyncSession,
        user_id: UUID,
        platform: str,
        body: str,
        idea_id: Optional[UUID] = None,
        version: int = 1,
        status: str = 'draft'
    ) -> ContentPost:
        """
        Создать новый пост
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
            platform: Платформа (telegram/instagram/threads)
            body: Текст поста
            idea_id: ID идеи (если пост создан из идеи)
            version: Версия поста
            status: Статус поста (draft/published)
        
        Returns:
            ContentPost: Созданный пост
        """
        try:
            post = ContentPost(
                user_id=user_id,
                platform=platform,
                body=body,
                idea_id=idea_id,
                version=version,
                status=status
            )
            
            session.add(post)
            await session.flush()
            
            logger.info(f"Создан пост для user_id={user_id}, post_id={post.id}, platform={platform}")
            
            return post
            
        except Exception as e:
            logger.error(f"Ошибка при создании поста: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_post(session: AsyncSession, post_id: UUID) -> Optional[ContentPost]:
        """
        Получить пост по ID
        
        Args:
            session: Async сессия БД
            post_id: ID поста
        
        Returns:
            ContentPost или None
        """
        try:
            result = await session.execute(
                select(ContentPost)
                .where(ContentPost.id == post_id)
            )
            
            post = result.scalar_one_or_none()
            
            return post
            
        except Exception as e:
            logger.error(f"Ошибка при получении поста: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_user_posts(
        session: AsyncSession,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[ContentPost]:
        """
        Получить посты пользователя
        
        Args:
            session: Async сессия БД
            user_id: ID пользоват еля
            limit: Лимит записей
            offset: Смещение для пагинации
            status: Фильтр по статусу (опционально)
        
        Returns:
            List[ContentPost]: Список постов
        """
        try:
            query = select(ContentPost).where(ContentPost.user_id == user_id)
            
            if status:
                query = query.where(ContentPost.status == status)
            
            query = query.order_by(desc(ContentPost.created_at)).limit(limit).offset(offset)
            
            result = await session.execute(query)
            posts = result.scalars().all()
            
            logger.debug(f"Получено {len(posts)} постов для user_id={user_id}")
            
            return list(posts)
            
        except Exception as e:
            logger.error(f"Ошибка при получении постов пользователя: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_latest_post_for_idea(
        session: AsyncSession,
        user_id: UUID,
        idea_id: UUID
    ) -> Optional[ContentPost]:
        """
        Получить последний пост для идеи
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
            idea_id: ID идеи
        
        Returns:
            ContentPost или None
        """
        try:
            result = await session.execute(
                select(ContentPost)
                .where(
                    and_(
                        ContentPost.user_id == user_id,
                        ContentPost.idea_id == idea_id
                    )
                )
                .order_by(desc(ContentPost.version), desc(ContentPost.created_at))
            )
            
            post = result.scalar_one_or_none()
            
            return post
            
        except Exception as e:
            logger.error(f"Ошибка при получении последнего поста для идеи: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def create_post_version(
        session: AsyncSession,
        original_post: ContentPost,
        new_body: str
    ) -> ContentPost:
        """
        Создать новую версию поста (при редактировании)
        
        Args:
            session: Async сессия БД
            original_post: Оригинальный пост
            new_body: Новый текст поста
        
        Returns:
            ContentPost: Новая версия поста
        """
        try:
            new_version = original_post.version + 1
            
            new_post = ContentPost(
                user_id=original_post.user_id,
                platform=original_post.platform,
                body=new_body,
                idea_id=original_post.idea_id,
                version=new_version,
                status='draft'
            )
            
            session.add(new_post)
            await session.flush()
            
            logger.info(f"Создана новая версия поста: post_id={new_post.id}, version={new_version}")
            
            return new_post
            
        except Exception as e:
            logger.error(f"Ошибка при создании новой версии поста: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_post_versions(
        session: AsyncSession,
        user_id: UUID,
        idea_id: UUID
    ) -> List[ContentPost]:
        """
        Получить все версии поста для идеи
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
            idea_id: ID идеи
        
        Returns:
            List[ContentPost]: Список версий постов
        """
        try:
            result = await session.execute(
                select(ContentPost)
                .where(
                    and_(
                        ContentPost.user_id == user_id,
                        ContentPost.idea_id == idea_id
                    )
                )
                .order_by(desc(ContentPost.version))
            )
            
            posts = result.scalars().all()
            
            logger.debug(f"Получено {len(posts)} версий поста для idea_id={idea_id}")
            
            return list(posts)
            
        except Exception as e:
            logger.error(f"Ошибка при получении версий поста: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def update_post_body(
        session: AsyncSession,
        post_id: UUID,
        new_body: str
    ) -> Optional[ContentPost]:
        """
        Обновить текст поста
        
        Args:
            session: Async сессия БД
            post_id: ID поста
            new_body: Новый текст поста
        
        Returns:
            ContentPost или None
        """
        try:
            post = await ContentPostsService.get_post(session, post_id)
            
            if not post:
                logger.warning(f"Пост не найден для обновления: post_id={post_id}")
                return None
            
            post.body = new_body
            post.updated_at = datetime.now(timezone.utc)
            
            await session.flush()
            
            logger.info(f"Текст поста обновлен: post_id={post_id}")
            
            return post
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении текста поста: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def count_user_posts(
        session: AsyncSession,
        user_id: UUID,
        status: Optional[str] = None
    ) -> int:
        """
        Подсчитать количество постов пользователя
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
            status: Фильтр по статусу (опционально)
        
        Returns:
            int: Количество постов
        """
        try:
            query = select(ContentPost).where(ContentPost.user_id == user_id)
            
            if status:
                query = query.where(ContentPost.status == status)
            
            result = await session.execute(query)
            count = len(result.scalars().all())
            
            return count
            
        except Exception as e:
            logger.error(f"Ошибка при подсчете постов: {e}", exc_info=True)
            return 0