from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from bot.database.models import User, RadarEvent
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class UserService:
    """
    Сервис для работы с пользователями.
    
    Правила:
    - Сервисы НЕ делают commit/rollback - это делает middleware
    - Используем session.add() и session.flush() для получения ID
    - Один запрос = одна транзакция (управляется middleware)
    """
    
    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        telegram_id: str,
        username: str = None,
        first_name: str = None,
        referral_code: str = None,
        bot_username: str = None
    ) -> User:
        """
        Получить или создать пользователя с обработкой гонки состояний (race condition).
        """
        # Пытаемся найти пользователя
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            # Пользователь не найден, пытаемся создать
            try:
                # Определяем реферера, если есть код
                referrer_id = None
                if referral_code:
                    referrer_result = await session.execute(
                        select(User).where(User.referral_code == referral_code)
                    )
                    referrer = referrer_result.scalar_one_or_none()
                    if referrer:
                        referrer_id = referrer.id
                        referrer.total_referrals += 1

                # Генерируем новый реферальный код для нового пользователя
                new_referral_code = str(uuid.uuid4())[:8]
                referral_link = f"https://t.me/{bot_username}?start={new_referral_code}" if bot_username else None

                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    referred_by_user_id=referrer_id,
                    subscription_status='FREE',
                    current_bot_menu='guest',
                    referral_code=new_referral_code,
                    telegram_bot_referral_link=referral_link,
                )
                session.add(user)
                await session.flush()  # Пытаемся сохранить, чтобы вызвать ошибку, если гонка состояний

            except IntegrityError:
                # Произошла гонка состояний: другой запрос создал пользователя между нашим SELECT и INSERT.
                # Откатываем сессию, чтобы очистить ее от неудачного объекта User.
                await session.rollback()
                # Теперь мы можем безопасно получить пользователя, который был создан другим запросом.
                result = await session.execute(select(User).where(User.telegram_id == telegram_id))
                user = result.scalar_one()

        # На этом этапе `user` гарантированно существует.
        # Обновляем данные при каждом входе.
        user.last_login = datetime.now()
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        
        # Генерируем реферальную ссылку, если ее нет
        if not user.telegram_bot_referral_link and bot_username:
            if not user.referral_code:
                user.referral_code = str(uuid.uuid4())[:8]
            user.telegram_bot_referral_link = f"https://t.me/{bot_username}?start={user.referral_code}"

        await session.flush()  # Сохраняем обновления в рамках транзакции
        return user
    
    @staticmethod
    async def get_user_by_telegram_id(session: AsyncSession, telegram_id: str) -> User:
        """Получить пользователя по telegram_id"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_subscription_status(
        session: AsyncSession,
        telegram_id: str,
        new_status: str
    ):
        """Обновить статус подписки пользователя и дату платежа."""
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(
                subscription_status=new_status,
                subscription_payment_date=datetime.now()
            )
        )
        # НЕ делаем commit - это сделает middleware
    
    @staticmethod
    async def update_all_voice_files(
        session: AsyncSession,
        telegram_id: str,
        **voice_ids
    ):
        """Обновить все голосовые файлы одним запросом"""
        update_values = {}
        
        if 'welcome_video_id' in voice_ids:
            update_values['welcome_video_id'] = voice_ids['welcome_video_id']
        if 'voice_passive_income_id' in voice_ids:
            update_values['voice_passive_income_id'] = voice_ids['voice_passive_income_id']
        if 'voice_free_travel_id' in voice_ids:
            update_values['voice_free_travel_id'] = voice_ids['voice_free_travel_id']
        if 'voice_freedom_id' in voice_ids:
            update_values['voice_freedom_id'] = voice_ids['voice_freedom_id']
        if 'voice_final_cta_id' in voice_ids:
            update_values['voice_final_cta_id'] = voice_ids['voice_final_cta_id']
        
        if update_values:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(**update_values)
            )
            # НЕ делаем commit - это сделает middleware
    
    @staticmethod
    async def update_welcome_video(session: AsyncSession, telegram_id: str, video_id: str):
        """Обновить ID видео-приветствия"""
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(welcome_video_id=video_id)
        )
        # НЕ делаем commit
    
    @staticmethod
    async def update_voice_passive_income(session: AsyncSession, telegram_id: str, voice_id: str):
        """Обновить ID голосового для ветки Пассивный доход"""
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(voice_passive_income_id=voice_id)
        )
        # НЕ делаем commit
    
    @staticmethod
    async def update_voice_travel(session: AsyncSession, telegram_id: str, voice_id: str):
        """Обновить ID голосового для ветки Путешествия"""
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(voice_free_travel_id=voice_id)
        )
        # НЕ делаем commit
    
    @staticmethod
    async def update_voice_freedom(session: AsyncSession, telegram_id: str, voice_id: str):
        """Обновить ID голосового для ветки Свобода"""
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(voice_freedom_id=voice_id)
        )
        # НЕ делаем commit
    
    @staticmethod
    async def update_voice_final(session: AsyncSession, telegram_id: str, voice_id: str):
        """Обновить ID финального голосового"""
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(voice_final_cta_id=voice_id)
        )
        # НЕ делаем commit
    
    @staticmethod
    async def get_referrer(session: AsyncSession, user: User) -> User:
        """Получить реферера пользователя"""
        if not user.referred_by_user_id:
            return None
        
        result = await session.execute(
            select(User).where(User.id == user.referred_by_user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def add_radar_event(
        session: AsyncSession,
        partner_id: uuid.UUID,
        lead_id: uuid.UUID,
        action_type: str
    ):
        """Добавить событие в радар"""
        event = RadarEvent(
            partner_id=partner_id,
            lead_id=lead_id,
            action_type=action_type
        )
        session.add(event)
        # НЕ делаем commit - это сделает middleware
    
    @staticmethod
    async def get_radar_events(session: AsyncSession, partner_id: uuid.UUID, limit: int = 10):
        """Получить последние события радара"""
        result = await session.execute(
            select(RadarEvent)
            .where(RadarEvent.partner_id == partner_id)
            .order_by(RadarEvent.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
