"""
Сервис для работы с профилями персонализации контент-мейкера
Следует принципам из RULEZ.md: один запрос = одна транзакция
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ContentPersonalProfile, ProfileVoiceSession, ProfileVoiceChunk

logger = logging.getLogger(__name__)


class ContentProfileService:
    """Сервис для работы с профилями персонализации"""
    
    @staticmethod
    async def get_profile(session: AsyncSession, user_id: UUID) -> Optional[ContentPersonalProfile]:
        """
        Получить профиль пользователя
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
        
        Returns:
            ContentPersonalProfile или None
        """
        try:
            result = await session.execute(
                select(ContentPersonalProfile)
                .where(ContentPersonalProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                logger.debug(f"Профиль найден для user_id={user_id}")
            else:
                logger.debug(f"Профиль не найден для user_id={user_id}")
            
            return profile
            
        except Exception as e:
            logger.error(f"Ошибка при получении профиля: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def has_profile(session: AsyncSession, user_id: UUID) -> bool:
        """
        Проверить, существует ли профиль у пользователя
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
        
        Returns:
            bool: True если профиль существует и заполнен
        """
        try:
            profile = await ContentProfileService.get_profile(session, user_id)
            
            if not profile:
                return False
            
            # Проверяем, что profile_data не пустой
            profile_data = profile.profile_data or {}
            
            # Профиль считается заполненным, если есть хотя бы базовая информация
            has_data = bool(
                profile_data.get('who_are_you') or 
                profile_data.get('character') or
                profile_data.get('raw_text')
            )
            
            return has_data
            
        except Exception as e:
            logger.error(f"Ошибка при проверке профиля: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def create_or_update_profile(
        session: AsyncSession,
        user_id: UUID,
        profile_data: Dict[str, Any]
    ) -> ContentPersonalProfile:
        """
        Создать или обновить профиль пользователя
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
            profile_data: Данные профиля (JSON)
        
        Returns:
            ContentPersonalProfile: Созданный или обновленный профиль
        """
        try:
            # Пытаемся найти существующий профиль
            existing = await ContentProfileService.get_profile(session, user_id)
            
            if existing:
                # Обновляем существующий профиль
                existing.profile_data = profile_data
                existing.updated_at = datetime.now(timezone.utc)
                
                # Используем flush для получения обновленных данных без commit
                await session.flush()
                
                logger.info(f"Профиль обновлен для user_id={user_id}")
                return existing
            else:
                # Создаем новый профиль
                new_profile = ContentPersonalProfile(
                    user_id=user_id,
                    profile_data=profile_data
                )
                session.add(new_profile)
                await session.flush()
                
                logger.info(f"Новый профиль создан для user_id={user_id}")
                return new_profile
                
        except Exception as e:
            logger.error(f"Ошибка при создании/обновлении профиля: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_profile_data(session: AsyncSession, user_id: UUID) -> Dict[str, Any]:
        """
        Получить данные профиля (только JSON)
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
        
        Returns:
            Dict с данными профиля или пустой dict
        """
        try:
            profile = await ContentProfileService.get_profile(session, user_id)
            
            if profile and profile.profile_data:
                return profile.profile_data
            
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных профиля: {e}", exc_info=True)
            return {}
    
    @staticmethod
    async def create_voice_session(session: AsyncSession, user_id: UUID) -> ProfileVoiceSession:
        """
        Создать новую голосовую сессию для заполнения профиля
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
        
        Returns:
            ProfileVoiceSession: Новая сессия
        """
        try:
            # Деактивируем все активные сессии пользователя
            await session.execute(
                update(ProfileVoiceSession)
                .where(ProfileVoiceSession.user_id == user_id)
                .where(ProfileVoiceSession.is_active == True)
                .values(is_active=False)
            )
            
            # Создаем новую сессию
            new_session = ProfileVoiceSession(
                user_id=user_id,
                is_active=True
            )
            session.add(new_session)
            await session.flush()
            
            logger.info(f"Создана голосовая сессия для user_id={user_id}, session_id={new_session.id}")
            
            return new_session
            
        except Exception as e:
            logger.error(f"Ошибка при создании голосовой сессии: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_active_voice_session(session: AsyncSession, user_id: UUID) -> Optional[ProfileVoiceSession]:
        """
        Получить активную голосовую сессию пользователя
        
        Args:
            session: Async сессия БД
            user_id: ID пользователя
        
        Returns:
            ProfileVoiceSession или None
        """
        try:
            result = await session.execute(
                select(ProfileVoiceSession)
                .where(ProfileVoiceSession.user_id == user_id)
                .where(ProfileVoiceSession.is_active == True)
                .order_by(ProfileVoiceSession.created_at.desc())
            )
            
            voice_session = result.scalar_one_or_none()
            
            if voice_session:
                logger.debug(f"Найдена активная голосовая сессия: session_id={voice_session.id}")
            
            return voice_session
            
        except Exception as e:
            logger.error(f"Ошибка при получении активной голосовой сессии: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def add_voice_chunk(
        session: AsyncSession,
        session_id: UUID,
        file_id: str,
        duration_seconds: Optional[int] = None
    ) -> ProfileVoiceChunk:
        """
        Добавить голосовой фрагмент в сессию
        
        Args:
            session: Async сессия БД
            session_id: ID голосовой сессии
            file_id: ID файла в Telegram
            duration_seconds: Длительность в секундах
        
        Returns:
            ProfileVoiceChunk: Добавленный фрагмент
        """
        try:
            # Получаем текущий максимальный sequence_number для этой сессии
            result = await session.execute(
                select(ProfileVoiceChunk)
                .where(ProfileVoiceChunk.session_id == session_id)
                .order_by(ProfileVoiceChunk.sequence_number.desc())
                .limit(1)
            )
            last_chunk = result.scalar_one_or_none()
            
            next_sequence = (last_chunk.sequence_number + 1) if last_chunk else 0
            
            # Создаем новый фрагмент
            chunk = ProfileVoiceChunk(
                session_id=session_id,
                file_id=file_id,
                duration_seconds=duration_seconds,
                sequence_number=next_sequence
            )
            session.add(chunk)
            await session.flush()
            
            logger.info(f"Добавлен голосовой фрагмент: session_id={session_id}, sequence={next_sequence}")
            
            return chunk
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении голосового фрагмента: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def get_session_voice_chunks(session: AsyncSession, session_id: UUID) -> List[ProfileVoiceChunk]:
        """
        Получить все голосовые фрагменты сессии
        
        Args:
            session: Async сессия БД
            session_id: ID голосовой сессии
        
        Returns:
            List[ProfileVoiceChunk]: Список фрагментов в порядке sequence_number
        """
        try:
            result = await session.execute(
                select(ProfileVoiceChunk)
                .where(ProfileVoiceChunk.session_id == session_id)
                .order_by(ProfileVoiceChunk.sequence_number.asc())
            )
            
            chunks = result.scalars().all()
            
            logger.debug(f"Получено {len(chunks)} голосовых фрагментов для session_id={session_id}")
            
            return list(chunks)
            
        except Exception as e:
            logger.error(f"Ошибка при получении голосовых фрагментов: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def close_voice_session(session: AsyncSession, session_id: UUID) -> None:
        """
        Закрыть голосовую сессию
        
        Args:
            session: Async сессия БД
            session_id: ID сессии
        """
        try:
            await session.execute(
                update(ProfileVoiceSession)
                .where(ProfileVoiceSession.id == session_id)
                .values(is_active=False)
            )
            
            await session.flush()
            
            logger.info(f"Голосовая сессия закрыта: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при закрытии голосовой сессии: {e}", exc_info=True)
            raise