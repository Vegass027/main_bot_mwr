from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, UUID, JSON, Numeric
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(String, unique=True, nullable=False, index=True)  # Индекс для быстрого поиска
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, index=True)  # Индекс для фильтрации активных пользователей
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # Индекс для сортировки
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), server_default=func.now())
    
    # Subscription
    subscription_status = Column(String, default='FREE', index=True)  # Индекс для фильтрации по статусу
    subscription_payment_date = Column(DateTime(timezone=True), nullable=True)
    
    # Referral system
    referral_code = Column(String, unique=True, nullable=True, index=True)  # Индекс для поиска реферера
    telegram_bot_referral_link = Column(String, nullable=True)
    referred_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)  # Индекс для JOIN
    total_referrals = Column(Integer, default=0)
    
    # Consultant info
    consultant_name = Column(String, nullable=True)
    consultant_photo_url = Column(String, nullable=True)
    consultant_description = Column(Text, nullable=True)
    consultant_instagram = Column(String, nullable=True)
    consultant_whatsapp = Column(Text, nullable=True)
    consultant_telegram = Column(String, nullable=True)
    consultant_email = Column(String, nullable=True)
    consultant_phone = Column(String, nullable=True)
    consultant_youtube = Column(String, nullable=True)
    
    # Bot settings
    
    # Voice messages for funnel personalization
    voice_passive_income_id = Column(String, nullable=True)
    voice_free_travel_id = Column(String, nullable=True)
    voice_freedom_id = Column(String, nullable=True)
    voice_final_cta_id = Column(String, nullable=True)
    voice_pay_less_id = Column(String, nullable=True)
    voice_5star_3star_id = Column(String, nullable=True)
    voice_travel_more_id = Column(String, nullable=True)
    voice_passive_income_final_id = Column(String, nullable=True)
    voice_free_travel_final_id = Column(String, nullable=True)
    voice_quit_job_final_id = Column(String, nullable=True)
    welcome_video_id = Column(String, nullable=True)
    current_bot_menu = Column(String, default='guest')
    business_instruction_link = Column(Text, nullable=True)
    
    # Links
    link_registration_mwr = Column(Text, nullable=True)
    link_travel_advantage = Column(Text, nullable=True)
    link_crypto_service = Column(Text, nullable=True)
    
    # Relationships
    referrer = relationship("User", remote_side=[id], backref="referrals")

class RadarEvent(Base):
    __tablename__ = 'radar_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)  # Индекс для выборки событий партнера
    lead_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    action_type = Column(Text, nullable=True, index=True)  # Индекс для фильтрации по типу действия
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # Индекс для сортировки по времени

class AIGeneration(Base):
    __tablename__ = 'ai_generations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)  # Индекс для выборки по пользователю
    telegram_message_id = Column(String, nullable=False, index=True)  # Индекс для быстрого поиска по message_id
    prompt = Column(Text, nullable=False)
    image_url = Column(Text, nullable=False)
    mode = Column(String, nullable=False, index=True)  # Индекс для фильтрации по режиму
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Индекс для очистки истекших

# AI-Тренажер модели
class Opponent(Base):
    """Модель профиля соперника для AI-тренажера"""
    __tablename__ = 'opponents'
    
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False)  # легкий, средний, сложный, эксперт
    age = Column(Integer, nullable=True)
    profession = Column(String(100), nullable=True)
    personality_type = Column(String(50), nullable=True)
    communication_style = Column(Text, nullable=True)
    core_objections = Column(JSON, nullable=True, default=list)
    triggers = Column(JSON, nullable=True, default=dict)
    response_patterns = Column(JSON, nullable=True, default=dict)
    base_prompt = Column(Text, nullable=False)
    voice_style = Column(Text, nullable=True)
    stats = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AITrainingSession(Base):
    """Модель сессии тренировки с AI-соперником"""
    __tablename__ = 'ai_training_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)  # Индекс для выборки сессий пользователя
    opponent_id = Column(String(50), ForeignKey('opponents.id', ondelete='CASCADE'), nullable=False, index=True)  # Индекс для JOIN и фильтрации
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # Индекс для сортировки
    ended_at = Column(DateTime(timezone=True), nullable=True)
    message_count = Column(Integer, default=0)
    user_score = Column(Numeric(3, 1), nullable=True, index=True)  # Индекс для статистики и ранжирования
    analysis = Column(Text, nullable=True)
    recommendations = Column(JSON, nullable=True, default=list)
    strengths = Column(JSON, nullable=True, default=list)
    weaknesses = Column(JSON, nullable=True, default=list)
    scores = Column(JSON, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, index=True)  # Индекс для поиска активных сессий
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="training_sessions")
    opponent = relationship("Opponent", backref="training_sessions")

class TrainingConversation(Base):
    """Модель истории диалогов в AI-тренажере"""
    __tablename__ = 'training_conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('ai_training_sessions.id', ondelete='CASCADE'), nullable=False, index=True)  # Индекс для выборки истории сессии
    role = Column(String(20), nullable=False)  # user, assistant, system
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # Индекс для сортировки по времени
    is_voice = Column(Boolean, default=False)
    voice_file_id = Column(Text, nullable=True)
    emotional_tone = Column(String(50), nullable=True)
    message_metadata = Column(JSON, nullable=True, default=dict)
    
    # Relationships
    session = relationship("AITrainingSession", backref="conversations")

class KnowledgeBase(Base):
    """Модель базы знаний для AI-тренажера"""
    __tablename__ = 'knowledge_base'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(100), nullable=False, index=True)  # Индекс для фильтрации по категории
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    keywords = Column(JSON, nullable=True, default=list)
    source_doc = Column(String(100), nullable=True, index=True)  # Индекс для группировки по источнику
    priority = Column(Integer, default=0, index=True)  # Индекс для сортировки по приоритету
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# Контент-Мейкер модели
class ContentPersonalProfile(Base):
    """Профиль персонализации для генерации контента"""
    __tablename__ = 'content_personal_profiles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    profile_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="content_profile")

class ProfileVoiceSession(Base):
    """Сессия голосового заполнения профиля"""
    __tablename__ = 'profile_voice_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)  # Индекс для поиска активных сессий
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="voice_sessions")

class ProfileVoiceChunk(Base):
    """Фрагменты голосовых сообщений в сессии"""
    __tablename__ = 'profile_voice_chunks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('profile_voice_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    file_id = Column(Text, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    sequence_number = Column(Integer, default=0, index=True)  # Индекс для сортировки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ProfileVoiceSession", backref="chunks")

class ContentType(Base):
    """Типы контента для генерации"""
    __tablename__ = 'content_types'
    
    id = Column(Integer, primary_key=True)
    code = Column(Text, unique=True, nullable=False, index=True)  # Индекс для поиска по коду
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    cta_strategy = Column(Text, nullable=False, default='ENGAGE')
    
class ContentIdea(Base):
    """Идеи контента для планирования"""
    __tablename__ = 'content_ideas'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content_type_id = Column(Integer, ForeignKey('content_types.id', ondelete='SET NULL'), nullable=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    platform = Column(Text, nullable=True, index=True)  # Индекс для фильтрации по платформе
    is_saved = Column(Boolean, default=False, index=True)  # Индекс для быстрого поиска сохраненных
    is_archived = Column(Boolean, default=False, index=True)  # Индекс для фильтрации архивных
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # Индекс для сортировки
    
    # Relationships
    user = relationship("User", backref="content_ideas")
    content_type = relationship("ContentType", backref="ideas")

class ContentPost(Base):
    """Сгенерированные посты"""
    __tablename__ = 'content_posts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    idea_id = Column(UUID(as_uuid=True), ForeignKey('content_ideas.id', ondelete='SET NULL'), nullable=True, index=True)
    platform = Column(Text, nullable=False, index=True)  # Индекс для фильтрации по платформе
    body = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    status = Column(Text, default='draft', index=True)  # Индекс для фильтрации по статусу
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # Индекс для сортировки
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="content_posts")
    idea = relationship("ContentIdea", backref="posts")