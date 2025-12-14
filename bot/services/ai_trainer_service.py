import os
import aiohttp
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update
import logging
import json

from bot.utils.cache import opponent_cache

logger = logging.getLogger(__name__)

class AITrainerService:
    """
    Сервис для работы с AI-тренажером возражений.
    
    Правила:
    - НЕ делает commit/rollback - это делает middleware
    - Используем session.flush() для получения ID
    - Кэширует opponent profiles для производительности
    """
    
    @staticmethod
    async def get_opponent_by_id(session: AsyncSession, opponent_id: str) -> Optional[Dict]:
        """
        Получить соперника по ID с кэшированием.
        
        Кэш TTL: 1 час (профили соперников редко меняются).
        """
        # Пытаемся получить из кэша
        cache_key = f"opponent:{opponent_id}"
        cached = opponent_cache.get(cache_key)
        if cached:
            return cached
        
        try:
            from bot.database.models import Opponent
            
            result = await session.execute(
                select(Opponent).where(Opponent.id == opponent_id)
            )
            row = result.scalar_one_or_none()
            if row:
                opponent_data = {
                    'id': row.id,
                    'name': row.name,
                    'difficulty': row.difficulty,
                    'age': row.age,
                    'profession': row.profession,
                    'personality_type': row.personality_type,
                    'communication_style': row.communication_style,
                    'core_objections': row.core_objections,
                    'triggers': row.triggers,
                    'response_patterns': row.response_patterns,
                    'base_prompt': row.base_prompt,
                    'voice_style': row.voice_style,
                    'stats': row.stats
                }
                
                # Сохраняем в кэш
                opponent_cache.set(cache_key, opponent_data)
                
                return opponent_data
            return None
        except Exception as e:
            logger.error(f"Ошибка получения соперника {opponent_id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def get_opponents_by_difficulty(session: AsyncSession, difficulty: Optional[str] = None) -> List[Dict]:
        """
        Получить список соперников с фильтром по сложности и кэшированием.
        
        Кэш TTL: 1 час.
        """
        # Пытаемся получить из кэша
        cache_key = f"opponents:difficulty:{difficulty or 'all'}"
        cached = opponent_cache.get(cache_key)
        if cached:
            return cached
        
        try:
            from bot.database.models import Opponent
            
            query = select(Opponent)
            if difficulty:
                query = query.where(Opponent.difficulty == difficulty)
            query = query.order_by(Opponent.difficulty, Opponent.name)
            
            result = await session.execute(query)
            opponents = result.scalars().all()
            
            opponents_data = [{
                'id': opp.id,
                'name': opp.name,
                'difficulty': opp.difficulty,
                'age': opp.age,
                'profession': opp.profession,
                'personality_type': opp.personality_type,
                'communication_style': opp.communication_style,
                'core_objections': opp.core_objections,
                'triggers': opp.triggers,
                'response_patterns': opp.response_patterns,
                'base_prompt': opp.base_prompt,
                'voice_style': opp.voice_style,
                'stats': opp.stats
            } for opp in opponents]
            
            # Сохраняем в кэш
            opponent_cache.set(cache_key, opponents_data)
            
            return opponents_data
        except Exception as e:
            logger.error(f"Ошибка получения списка соперников: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def create_training_session(
        session: AsyncSession,
        user_id: str,
        opponent_id: str
    ) -> Optional[str]:
        """Создать новую сессию тренировки"""
        try:
            from bot.database.models import AITrainingSession
            
            new_session = AITrainingSession(
                user_id=user_id,
                opponent_id=opponent_id,
                is_active=True
            )
            session.add(new_session)
            await session.flush()  # Получаем ID без commit
            
            return str(new_session.id)
        except Exception as e:
            logger.error(f"Ошибка создания сессии тренировки: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def get_active_session(session: AsyncSession, user_id: str) -> Optional[Dict]:
        """Получить активную сессию пользователя"""
        try:
            from bot.database.models import AITrainingSession
            import uuid
            
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            result = await session.execute(
                select(AITrainingSession)
                .where(and_(
                    AITrainingSession.user_id == user_uuid,
                    AITrainingSession.is_active == True
                ))
            )
            row = result.scalar_one_or_none()
            if row:
                return {
                    'id': str(row.id),
                    'user_id': str(row.user_id),
                    'opponent_id': row.opponent_id,
                    'is_active': row.is_active,
                    'message_count': row.message_count
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка получения активной сессии: {e}")
            return None
    
    @staticmethod
    async def add_message_to_session(
        session: AsyncSession,
        session_id: str,
        role: str,
        message: str,
        is_voice: bool = False,
        voice_file_id: Optional[str] = None,
        emotional_tone: Optional[str] = None
    ) -> bool:
        """Добавить сообщение в историю диалога"""
        try:
            from bot.database.models import TrainingConversation, AITrainingSession
            from sqlalchemy import UUID as SQLAlchemyUUID
            import uuid
            
            new_message = TrainingConversation(
                session_id=uuid.UUID(session_id) if isinstance(session_id, str) else session_id,
                role=role,
                message=message,
                is_voice=is_voice,
                voice_file_id=voice_file_id,
                emotional_tone=emotional_tone
            )
            session.add(new_message)
            
            # Обновляем счетчик сообщений в сессии
            await session.execute(
                update(AITrainingSession)
                .where(AITrainingSession.id == uuid.UUID(session_id) if isinstance(session_id, str) else session_id)
                .values(
                    message_count=AITrainingSession.message_count + 1,
                    updated_at=datetime.utcnow()
                )
            )
            
            # НЕ делаем commit - это сделает middleware
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления сообщения: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def get_session_history(
        session: AsyncSession,
        session_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Получить последние N сообщений из истории"""
        try:
            from bot.database.models import TrainingConversation
            import uuid
            
            result = await session.execute(
                select(TrainingConversation)
                .where(TrainingConversation.session_id == uuid.UUID(session_id) if isinstance(session_id, str) else session_id)
                .order_by(TrainingConversation.timestamp.desc())
                .limit(limit)
            )
            conversations = result.scalars().all()
            
            messages = [{
                'id': str(conv.id),
                'session_id': str(conv.session_id),
                'role': conv.role,
                'message': conv.message,
                'timestamp': conv.timestamp,
                'is_voice': conv.is_voice,
                'voice_file_id': conv.voice_file_id,
                'emotional_tone': conv.emotional_tone
            } for conv in conversations]
            
            return list(reversed(messages))  # Вернуть в хронологическом порядке
        except Exception as e:
            logger.error(f"Ошибка получения истории сессии: {e}")
            return []
    
    @staticmethod
    async def end_training_session(
        session: AsyncSession,
        session_id: str,
        user_score: Optional[float] = None,
        analysis: Optional[str] = None,
        scores: Optional[Dict] = None,
        strengths: Optional[List[str]] = None,
        weaknesses: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None
    ) -> bool:
        """Завершить сессию тренировки"""
        try:
            from bot.database.models import AITrainingSession
            import uuid
            
            update_data = {
                'is_active': False,
                'ended_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            if user_score is not None:
                update_data['user_score'] = user_score
            if analysis:
                update_data['analysis'] = analysis
            if scores:
                update_data['scores'] = scores
            if strengths:
                update_data['strengths'] = strengths
            if weaknesses:
                update_data['weaknesses'] = weaknesses
            if recommendations:
                update_data['recommendations'] = recommendations
            
            await session.execute(
                update(AITrainingSession)
                .where(AITrainingSession.id == uuid.UUID(session_id) if isinstance(session_id, str) else session_id)
                .values(**update_data)
            )
            
            # НЕ делаем commit - это сделает middleware
            return True
        except Exception as e:
            logger.error(f"Ошибка завершения сессии: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def get_user_statistics(session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Получить статистику пользователя"""
        try:
            from bot.database.models import AITrainingSession, Opponent
            import uuid
            
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Общее количество тренировок
            total_result = await session.execute(
                select(func.count(AITrainingSession.id))
                .where(AITrainingSession.user_id == user_uuid)
            )
            total_sessions = total_result.scalar()
            
            # Средний балл
            avg_result = await session.execute(
                select(func.avg(AITrainingSession.user_score))
                .where(and_(
                    AITrainingSession.user_id == user_uuid,
                    AITrainingSession.user_score.isnot(None)
                ))
            )
            avg_score = avg_result.scalar() or 0
            
            # Последние 5 тренировок с данными соперника
            recent_result = await session.execute(
                select(AITrainingSession, Opponent)
                .join(Opponent, AITrainingSession.opponent_id == Opponent.id)
                .where(AITrainingSession.user_id == user_uuid)
                .order_by(AITrainingSession.started_at.desc())
                .limit(5)
            )
            recent_data = recent_result.all()
            
            recent_sessions = [{
                'opponent_name': opp.name,
                'opponent_id': opp.id,
                'user_score': float(sess.user_score) if sess.user_score else 0,
                'started_at': sess.started_at,
                'message_count': sess.message_count
            } for sess, opp in recent_data]
            
            return {
                'total_sessions': total_sessions or 0,
                'average_score': round(float(avg_score), 1) if avg_score else 0,
                'recent_sessions': recent_sessions
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'total_sessions': 0,
                'average_score': 0,
                'recent_sessions': []
            }
    
    @staticmethod
    async def analyze_intent(message: str) -> Dict[str, Any]:
        """Простой анализ интента сообщения по ключевым словам"""
        keywords = {
            'prices': ['сколько', 'цена', 'стоимость', 'дешевле', 'booking', 'дорого', 'платить'],
            'legality': ['легально', 'документ', 'лицензия', 'пирамида', 'iata', 'законно', 'мошенник'],
            'how_it_works': ['как работает', 'принцип', 'откуда', 'почему', 'как это'],
            'earnings': ['заработок', 'доход', 'сколько зарабат', 'компенсация', 'млм', 'сетевой'],
            'trust': ['доверять', 'обман', 'развод', 'лохотрон', 'отзыв', 'правда']
        }
        
        lower_message = message.lower()
        detected_topics = []
        
        for topic, words in keywords.items():
            if any(word in lower_message for word in words):
                detected_topics.append(topic)
        
        return {
            'topics': detected_topics,
            'needs_facts': len(detected_topics) > 0,
            'message_length': len(message.split())
        }
    
    @staticmethod
    async def get_relevant_knowledge(
        session: AsyncSession,
        topics: List[str]
    ) -> List[Dict]:
        """Получить релевантную информацию из базы знаний"""
        try:
            if not topics:
                return []
            
            # Мапинг топиков на категории в БД
            topic_to_category = {
                'prices': 'цены',
                'legality': 'легальность',
                'how_it_works': 'как_работает',
                'earnings': 'компенсация',
                'trust': 'доверие'
            }
            
            categories = [topic_to_category.get(t, t) for t in topics]
            
            result = await session.execute(
                select('knowledge_base')
                .where('knowledge_base.category'.in_(categories))
                .order_by('knowledge_base.priority'.desc())
                .limit(5)
            )
            
            return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения знаний: {e}")
            return []
    
    @staticmethod
    async def analyze_training_session(
        conversation_history: List[Dict],
        opponent_name: str
    ) -> Dict[str, Any]:
        """Анализ тренировочной сессии через OpenAI"""
        try:
            api_key = os.getenv('OPEN_AI_API_KEY')
            if not api_key:
                logger.error("OPEN_AI_API_KEY не найден")
                return None
            
            # Формируем диалог для анализа
            dialogue = ""
            for msg in conversation_history:
                role_label = "Клиент" if msg['role'] == 'assistant' else "Вы"
                dialogue += f"{role_label}: {msg['message']}\n"
            
            analysis_prompt = f"""Ты эксперт по продажам и работе с возражениями. Проанализируй диалог между менеджером по продажам и клиентом ({opponent_name}).

ДИАЛОГ:
{dialogue}

Проведи детальный анализ и выдай результат в следующем JSON формате:

{{
  "scores": {{
    "product_knowledge": 8.5,
    "objection_handling": 7.0,
    "emotional_intelligence": 9.0,
    "confidence": 8.0
  }},
  "overall_score": 8.1,
  "strengths": [
    "Конкретная сильная сторона 1",
    "Конкретная сильная сторона 2",
    "Конкретная сильная сторона 3"
  ],
  "weaknesses": [
    "Конкретная слабая сторона 1",
    "Конкретная слабая сторона 2"
  ],
  "recommendations": [
    "Конкретная рекомендация 1",
    "Конкретная рекомендация 2",
    "Конкретная рекомендация 3"
  ],
  "summary": "Краткий общий анализ производительности (2-3 предложения)"
}}

КРИТЕРИИ ОЦЕНКИ (от 1 до 10):
- product_knowledge: Знание продукта, точность информации, умение объяснять
- objection_handling: Работа с возражениями, аргументация, переход через барьеры
- emotional_intelligence: Эмпатия, понимание клиента, адаптация стиля общения
- confidence: Уверенность, профессионализм, контроль диалога

overall_score - среднее арифметическое всех оценок

Будь конкретным в strengths, weaknesses и recommendations. Приводи примеры из диалога."""

            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'gpt-4o-mini',
                        'messages': [
                            {'role': 'system', 'content': 'Ты эксперт по анализу продаж и тренингам. Отвечай только в JSON формате.'},
                            {'role': 'user', 'content': analysis_prompt}
                        ],
                        'temperature': 0.7,
                        'response_format': {'type': 'json_object'}
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        analysis_text = result['choices'][0]['message']['content']
                        return json.loads(analysis_text)
                    else:
                        logger.error(f"Ошибка API OpenAI: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка анализа сессии: {e}")
            return None
    
    @staticmethod
    async def transcribe_voice(file_path: str) -> Optional[str]:
        """Транскрибировать голосовое сообщение через Whisper API"""
        try:
            api_key = os.getenv('OPEN_AI_API_KEY')
            if not api_key:
                logger.error("OPEN_AI_API_KEY не найден")
                return None
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as audio_file:
                    form = aiohttp.FormData()
                    form.add_field('file', audio_file, filename='audio.ogg')
                    form.add_field('model', 'gpt-4o-mini-transcribe')
                    form.add_field('language', 'ru')
                    
                    async with session.post(
                        'https://api.openai.com/v1/audio/transcriptions',
                        headers={'Authorization': f'Bearer {api_key}'},
                        data=form
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result.get('text')
                        else:
                            logger.error(f"Ошибка транскрибации: {response.status}")
                            return None
        except Exception as e:
            logger.error(f"Ошибка транскрибации голоса: {e}")
            return None
    
    @staticmethod
    async def search_in_documents(
        session: AsyncSession,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """Поиск релевантной информации в таблице documents через векторный поиск"""
        try:
            # Сначала получаем embedding для запроса через OpenAI
            api_key = os.getenv('OPEN_AI_API_KEY')
            if not api_key:
                logger.error("OPEN_AI_API_KEY не найден")
                return []
            
            async with aiohttp.ClientSession() as http_session:
                # Генерируем embedding для запроса
                async with http_session.post(
                    'https://api.openai.com/v1/embeddings',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'input': query,
                        'model': 'text-embedding-ada-002'
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка получения embedding: {response.status}")
                        return []
                    
                    result = await response.json()
                    query_embedding = result['data'][0]['embedding']
            
            # Выполняем векторный поиск в БД
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            query_sql = f"""
            SELECT content, metadata,
                   1 - (embedding <=> '{embedding_str}'::vector) as similarity
            FROM documents
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT {limit};
            """
            
            result = await session.execute(query_sql)
            return [dict(row._mapping) for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"Ошибка поиска в documents: {e}")
            return []
    
    @staticmethod
    async def generate_ai_response(
        opponent_prompt: str,
        conversation_history: List[Dict],
        user_message: str,
        relevant_knowledge: List[Dict]
    ) -> Optional[str]:
        """Генерация ответа AI-соперника через OpenAI GPT-4"""
        try:
            api_key = os.getenv('OPEN_AI_API_KEY')
            if not api_key:
                logger.error("OPEN_AI_API_KEY не найден")
                return None
            
            # Формируем контекст из базы знаний / documents
            knowledge_context = ""
            if relevant_knowledge:
                knowledge_context = "\n\n# РЕЛЕВАНТНЫЕ ФАКТЫ О ПРОДУКТЕ:\n"
                for item in relevant_knowledge:
                    # Если это из documents
                    if 'content' in item:
                        knowledge_context += f"\n{item['content'][:500]}...\n"
                    # Если это из knowledge_base
                    elif 'question' in item and 'answer' in item:
                        knowledge_context += f"\nQ: {item['question']}\nA: {item['answer']}\n"
            
            # Формируем историю диалога
            history_text = ""
            for msg in conversation_history[-6:]:  # Последние 6 сообщений
                role_label = "Пользователь" if msg['role'] == 'user' else "Ты"
                history_text += f"{role_label}: {msg['message']}\n"
            
            # Формируем финальный промпт
            system_content = f"{opponent_prompt}{knowledge_context}"
            
            user_content = f"""# КОНТЕКСТ ДИАЛОГА
{history_text}

# НОВОЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ
{user_message}

Ответь В РОЛИ соперника, учитывая его психологию и паттерны поведения. НЕ повторяйся."""
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'gpt-4o',
                        'messages': [
                            {'role': 'system', 'content': system_content},
                            {'role': 'user', 'content': user_content}
                        ],
                        'max_tokens': 500,
                        'temperature': 0.8
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка OpenAI API: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка генерации ответа AI: {e}")
            return None