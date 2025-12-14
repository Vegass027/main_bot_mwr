"""
LLM Service для работы с OpenAI/Anthropic API
Используется для генерации контента, парсинга профилей и редактирования постов
"""

import os
import json
import logging
from typing import Dict, Any, List, Literal, Optional
from openai import AsyncOpenAI
import aiohttp
from bot.utils.http_client import HTTPClientManager

logger = logging.getLogger(__name__)


class LLMService:
    """Сервис для работы с LLM (OpenAI/Anthropic)"""
    
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'openai')
        self.api_key = os.getenv('OPEN_AI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OPEN_AI_API_KEY не найден в .env")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = os.getenv('LLM_MODEL', 'gpt-4-turbo-preview')
        
        logger.info(f"LLM Service инициализирован: provider={self.provider}, model={self.model}")
    
    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Literal['text', 'json'] = 'text'
    ) -> str:
        """
        Универсальный метод для генерации completion
        
        Args:
            prompt: Основной промпт
            system_prompt: Системный промпт (опционально)
            temperature: Температура (0-1)
            max_tokens: Максимальное количество токенов
            response_format: Формат ответа ('text' или 'json')
        
        Returns:
            str: Сгенерированный текст
        """
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            # Параметры запроса
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Для JSON ответа используем response_format
            if response_format == 'json':
                kwargs["response_format"] = {"type": "json_object"}
            
            # Выполняем запрос
            response = await self.client.chat.completions.create(**kwargs)
            
            result = response.choices[0].message.content
            
            logger.info(f"LLM completion успешно сгенерирован (tokens: {response.usage.total_tokens})")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при генерации completion: {e}", exc_info=True)
            raise
    
    async def parse_profile_from_text(self, user_text: str) -> Dict[str, Any]:
        """
        Парсинг профиля пользователя из текста или транскрипта
        
        Args:
            user_text: Текст от пользователя о себе
        
        Returns:
            Dict с структурированным профилем
        """
        system_prompt = """Ты — помощник, который структурирует информацию о пользователе для персонализации контента.
Извлекай информацию точно и корректно. Если информация не указана, используй null или пустой массив.
ВАЖНО: Возвращай ТОЛЬКО валидный JSON без лишних символов и комментариев."""
        
        # Ограничиваем длину входного текста для избежания проблем с токенами
        max_input_length = 3000
        if len(user_text) > max_input_length:
            user_text = user_text[:max_input_length] + "..."
            logger.warning(f"Текст профиля обрезан до {max_input_length} символов")
        
        prompt = f"""Пользователь рассказал о себе:
\"\"\"
{user_text}
\"\"\"

Извлеки следующую информацию и верни в формате JSON:

{{
  "who_are_you": {{
    "name": "имя",
    "age": возраст (число или null),
    "city": "город",
    "occupation": "род занятий",
    "expertise": "в чём разбирается"
  }},
  "travel_experience": {{
    "level": "новичок/бывалый/эксперт",
    "countries_count": число или null,
    "style": "эконом/лакшери/соло/семья/смешанный",
    "dream_destination": "мечта о поездке"
  }},
  "character": {{
    "communication_style": "дерзко/по-дружески/официально/с юмором/смешанный",
    "topics_of_interest": ["тема1", "тема2"],
    "pet_peeves": ["что бесит1", "что бесит2"]
  }},
  "goals": {{
    "main_goals": ["цель1", "цель2"],
    "current_passion": "чем горит сейчас"
  }}
}}

Если информация не указана, используй null или пустой массив.
Верни ТОЛЬКО валидный JSON, без пояснений и комментариев."""
        
        try:
            response_text = await self.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2000,
                response_format='json'
            )
            
            # Очищаем ответ от возможных markdown блоков
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Пытаемся распарсить JSON
            try:
                profile_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Первая попытка парсинга JSON не удалась: {e}")
                logger.error(f"Ответ LLM (первые 500 символов): {response_text[:500]}...")
                
                # Пытаемся исправить распространенные проблемы
                # Удаляем комментарии
                import re
                response_text = re.sub(r'//.*?\n', '\n', response_text)
                response_text = re.sub(r'/\*.*?\*/', '', response_text, flags=re.DOTALL)
                
                # Повторная попытка
                profile_data = json.loads(response_text)
            
            logger.info("Профиль успешно распарсен из текста")
            
            return profile_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON профиля: {e}")
            logger.error(f"Проблемный текст: {response_text if 'response_text' in locals() else 'не получен'}")
            
            # Возвращаем базовый профиль в случае ошибки
            return {
                "who_are_you": {
                    "name": "Не указано",
                    "age": None,
                    "city": "Не указан",
                    "occupation": "Не указано",
                    "expertise": "Не указана"
                },
                "travel_experience": {
                    "level": "средний",
                    "countries_count": None,
                    "style": "смешанный",
                    "dream_destination": None
                },
                "character": {
                    "communication_style": "дружелюбный",
                    "topics_of_interest": [],
                    "pet_peeves": []
                },
                "goals": {
                    "main_goals": ["развитие"],
                    "current_passion": None
                }
            }
        except Exception as e:
            logger.error(f"Ошибка при парсинге профиля: {e}", exc_info=True)
            raise
    
    async def generate_content_ideas(
        self,
        profile_data: Dict[str, Any],
        content_type_name: str,
        content_type_description: str,
        platform: str
    ) -> List[Dict[str, str]]:
        """
        Генерация идей для контента
        
        Args:
            profile_data: Профиль пользователя
            content_type_name: Название типа контента
            content_type_description: Описание типа контента
            platform: Платформа (telegram/instagram/threads)
        
        Returns:
            List из 6 идей с title, description, hook
        """
        # Извлекаем данные из профиля
        who = profile_data.get('who_are_you', {})
        travel = profile_data.get('travel_experience', {})
        character = profile_data.get('character', {})
        goals = profile_data.get('goals', {})
        
        system_prompt = "Ты — креативный помощник контент-мейкера для партнёров экосистемы путешествий."
        
        prompt = f"""ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
- Имя: {who.get('name', 'не указано')}, {who.get('age', 'возраст не указан')} лет, {who.get('city', 'город не указан')}
- Род занятий: {who.get('occupation', 'не указано')}
- Экспертиза: {who.get('expertise', 'не указано')}
- Travel опыт: {travel.get('level', 'не указан')}, {travel.get('countries_count', 'не указано')} стран, стиль: {travel.get('style', 'не указан')}
- Стиль общения: {character.get('communication_style', 'не указан')}
- Интересы: {', '.join(character.get('topics_of_interest', ['не указаны']))}
- Цели: {', '.join(goals.get('main_goals', ['не указаны']))}
- Страсть сейчас: {goals.get('current_passion', 'не указана')}

ТИП КОНТЕНТА: {content_type_name}
Описание типа: {content_type_description}

ПЛАТФОРМА: {platform}

ЗАДАЧА: Сгенерируй 6 идей для постов в этом типе контента.

ТРЕБОВАНИЯ:
1. Каждая идея должна быть ПЕРСОНАЛИЗИРОВАННОЙ (на основе профиля пользователя)
2. Идеи должны быть РАЗНООБРАЗНЫМИ (разные углы, подходы)
3. Идеи должны ВЫЗЫВАТЬ ВОПРОСЫ у аудитории (не давать готовые ответы)
4. Учитывай формат платформы:
   - Telegram: прямолинейно, с эмодзи, 1000-1200 символов
   - Instagram: красиво, с описанием к фото, хэштеги
   - Threads: логичный тред, как колонка

ФОРМАТ ОТВЕТА (JSON):
{{
  "ideas": [
    {{
      "title": "Краткое название идеи (30-50 символов)",
      "description": "Развёрнутое описание: о чём пост, какой угол, что показать (100-150 символов)",
      "hook": "Цепляющее начало поста (20-30 символов)"
    }}
  ]
}}

Верни ТОЛЬКО JSON, без пояснений."""
        
        try:
            response_text = await self.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=2000,
                response_format='json'
            )
            
            result = json.loads(response_text)
            ideas = result.get('ideas', [])
            
            logger.info(f"Сгенерировано {len(ideas)} идей для контента")
            
            return ideas
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON идей: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при генерации идей: {e}", exc_info=True)
            raise
    
    async def generate_post(
        self,
        profile_data: Dict[str, Any],
        idea_title: str,
        idea_description: str,
        content_type_name: str,
        platform: str
    ) -> str:
        """
        Генерация готового поста
        
        Args:
            profile_data: Профиль пользователя
            idea_title: Название идеи
            idea_description: Описание идеи
            content_type_name: Тип контента
            platform: Платформа
        
        Returns:
            str: Готовый текст поста
        """
        who = profile_data.get('who_are_you', {})
        travel = profile_data.get('travel_experience', {})
        character = profile_data.get('character', {})
        goals = profile_data.get('goals', {})
        
        system_prompt = "Ты — профессиональный копирайтер контент-мейкера для партнёров экосистемы путешествий."
        
        prompt = f"""ПРОФИЛЬ АВТОРА:
- Имя: {who.get('name', 'не указано')}, {who.get('age', 'возраст не указан')} лет, {who.get('city', 'город не указан')}
- Род занятий: {who.get('occupation', 'не указано')}
- Экспертиза: {who.get('expertise', 'не указано')}
- Travel опыт: {travel.get('level', 'не указан')}, {travel.get('countries_count', 'не указано')} стран
- Стиль общения: {character.get('communication_style', 'не указан')}
- Что раздражает: {', '.join(character.get('pet_peeves', ['не указано']))}
- Цели: {', '.join(goals.get('main_goals', ['не указаны']))}

ТИП КОНТЕНТА: {content_type_name}
ПЛАТФОРМА: {platform}

ИДЕЯ ПОСТА:
Название: {idea_title}
Описание: {idea_description}

ЗАДАЧА: Напиши готовый пост для этой платформы.

ТРЕБОВАНИЯ:
1. Пиши ГОЛОСОМ АВТОРА (его стиль общения, лексика)
2. Используй РЕАЛЬНЫЕ ДЕТАЛИ из профиля (город, опыт, занятия)
3. НЕ ДАВАЙ ГОТОВЫХ ОТВЕТОВ — создавай интригу, вопросы
4. Структура поста:
   - Цепляющее начало (hook)
   - Основная часть (история/факты/мысли)
   - Вопрос к аудитории или открытый финал (НЕ призыв к действию!)

5. Формат для платформы:
   - Telegram: 1000-1200 символов, эмодзи умеренно, абзацы по 2-3 предложения
   - Instagram: 1200-1500 символов, больше эмодзи, 5-10 хэштегов в конце
   - Threads: 1500-2000 символов, логичная структура, без хэштегов

6. ИЗБЕГАЙ:
   - Банальностей и клише
   - Прямых призывов "Переходи в бот", "Подпишись"
   - Слишком продающих формулировок
   - Шаблонных вопросов типа "А как у тебя?"

7. ТОН: {character.get('communication_style', 'дружелюбный')}

Верни ТОЛЬКО текст поста, без пояснений и комментариев."""
        
        try:
            post_text = await self.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=2500,
                response_format='text'
            )
            
            logger.info("Пост успешно сгенерирован")
            
            return post_text.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {e}", exc_info=True)
            raise
    
    async def edit_post(
        self,
        original_post: str,
        edit_instruction: str,
        profile_data: Dict[str, Any]
    ) -> str:
        """
        Редактирование поста по инструкции
        
        Args:
            original_post: Оригинальный текст поста
            edit_instruction: Инструкция по редактированию
            profile_data: Профиль пользователя
        
        Returns:
            str: Отредактированный текст поста
        """
        who = profile_data.get('who_are_you', {})
        character = profile_data.get('character', {})
        
        system_prompt = "Ты — редактор контент-мейкера для партнёров экосистемы путешествий."
        
        prompt = f"""ОРИГИНАЛЬНЫЙ ПОСТ:
\"\"\"
{original_post}
\"\"\"

ПРОФИЛЬ АВТОРА:
- Стиль общения: {character.get('communication_style', 'не указан')}
- Имя: {who.get('name', 'не указано')}, {who.get('occupation', 'не указано')}

ИНСТРУКЦИЯ ПО РЕДАКТИРОВАНИЮ:
"{edit_instruction}"

ЗАДАЧА: Отредактируй пост согласно инструкции, сохраняя стиль автора.

ТРЕБОВАНИЯ:
1. Если инструкция касается конкретного абзаца/части — редактируй только её
2. Если инструкция общая ("добавь эмодзи", "сделай дерзче") — редактируй весь пост
3. Сохраняй стиль автора ({character.get('communication_style', 'дружелюбный')})
4. НЕ ДОБАВЛЯЙ призывы к действию, если их не было
5. Сохраняй длину поста примерно такой же (±10%)

Верни ТОЛЬКО отредактированный текст поста, без пояснений."""
        
        try:
            edited_post = await self.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2500,
                response_format='text'
            )
            
            logger.info("Пост успешно отредактирован")
            
            return edited_post.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при редактировании поста: {e}", exc_info=True)
            raise


# Singleton инстанс
_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Получить singleton инстанс LLM сервиса"""
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    
    return _llm_service_instance