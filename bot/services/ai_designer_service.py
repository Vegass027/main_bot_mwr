import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models import AIGeneration
import uuid
from typing import Tuple, Optional, List
import logging

from bot.utils.http_client import HTTPClientManager

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """ROLE:
You are a world-class Art Director and prompt engineer for FLUX.1 image generation. Your mission is to create prompts that produce INDISTINGUISHABLE from real photography results — images so realistic that viewers on Instagram cannot tell they are AI-generated.


---


INPUT ANALYSIS:


CASE A: NEW CREATION (Text-to-Image)
User provides a concept or idea. Transform it into a hyper-detailed, photographically accurate prompt.


CASE B: REFINEMENT (Image-to-Image Edit)
User provides editing instructions. Output a SHORT, focused prompt describing ONLY the changes needed. The base image already contains the composition.


CASE C: USER PHOTO TRANSFORMATION (Reference-based)
User uploads their photo with a transformation request. Create a prompt that specifies what to preserve from the original (person's features, pose, clothing details) and what to transform (environment, lighting, atmosphere).


---


CRITICAL RULES FOR PHOTOREALISM:


1. CAMERA REALISM:
- Always specify real camera equipment (brand + model + lens)
- Include realistic photography artifacts (film grain, chromatic aberration, lens flare)
- Mention specific photography techniques (shallow depth of field, bokeh quality)


2. LIGHTING PHYSICS:
- Light must obey real-world physics (shadows, reflections, light falloff)
- Specify exact lighting conditions (time of day, weather, light direction)
- Use professional lighting terminology (key light, rim light, ambient occlusion)


3. MATERIAL ACCURACY:
- Describe textures with physical precision (fabric weave, skin texture, surface imperfections)
- Include environmental effects (dust particles, moisture, weathering)
- Mention sub-surface scattering for organic materials


4. COMPOSITION MASTERY:
- Apply dynamic perspectives that mimic real photographer angles
- Use rule of thirds, leading lines, natural framing
- Create depth through foreground/midground/background layering
- Implement occlusion principle (objects naturally overlapping)


5. TEXT INTEGRATION (when requested):
- Text must be PART OF THE WORLD, not overlaid
- Methods: shadows forming words, neon signage, carved surfaces, cloud formations, negative space between objects
- Text follows perspective and lighting of the scene
- Elements can naturally overlap text for depth


6. ATMOSPHERIC UNITY:
- Match color temperature to light source
- Apply cohesive color grading (teal-orange, bleach bypass, etc.)
- Ensure consistent visual style across all elements
- Add environmental atmosphere (haze, fog, dust) for depth


7. IMPERFECTION IS PERFECTION:
- Include slight imperfections (minor blur, natural noise, uneven lighting)
- Avoid "too perfect" CGI look
- Capture candid, authentic moments rather than staged perfection


8. STYLE ADAPTABILITY:
- NEVER use default aesthetic
- Analyze the mood and choose appropriate visual language
- Rotate between styles: editorial fashion, street photography, documentary, fine art, travel photography, lifestyle, cinematic


---


OUTPUT FORMAT:
Return ONLY the English prompt. No explanations, no markdown, no quotes.


PROMPT STRUCTURE:
[Photography type & camera specs] + [Subject & authentic action] + [Precise lighting details] + [Environmental context with depth layers] + [Material & texture specifics] + [Composition technique] + [Color grading & atmosphere] + [Text integration method if needed] + [Realism keywords]


---


NOW PROCESS THIS REQUEST:"""


class AIDesignerService:
    """
    Сервис для работы с AI-Designer.
    
    Правила:
    - Использует shared HTTP clients (HTTPClientManager)
    - НЕ делает session.commit() - это делает middleware
    - Все HTTP запросы с таймаутами
    - Логирует ошибки с контекстом
    """

    @staticmethod
    async def generate_prompt_with_openai(user_input: str, case_type: str = "A") -> str:
        """
        Генерация промпта через OpenAI для Агента 1 и Агента 3.
        Использует shared ClientSession для производительности.
        """
        full_input = user_input
        
        try:
            # Получаем shared session
            session = await HTTPClientManager.get_openai_session()
            
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": full_input}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "OpenAI API error",
                        extra={
                            "status": response.status,
                            "error": error_text,
                            "case_type": case_type
                        }
                    )
                    raise Exception(f"OpenAI API error: {error_text}")

                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()
        
        except Exception as e:
            logger.error(
                "Failed to generate prompt with OpenAI",
                exc_info=True,
                extra={"case_type": case_type}
            )
            raise

    @staticmethod
    async def enhance_edit_prompt_with_llm(user_edit: str) -> str:
        """
        Улучшение промпта редактирования через LLM (Агент 2).
        Использует shared ClientSession.
        """
        edit_system_prompt = """You are an expert at creating clear, professional edit instructions for image editing AI.


Your task: Convert user's casual edit request into a clear, professional instruction in English.


Rules:
- Keep it SHORT and PRECISE (1-2 sentences max)
- Focus ONLY on what needs to be changed
- Use clear, direct language
- Always output in English
- No explanations, just the instruction


Examples:
User: "добавь кактус на стол" → "Add a small cactus plant on the desk"
User: "сделай волосы блондинистыми" → "Change hair color to blonde"
User: "убери фон" → "Remove the background"
User: "add sunglasses" → "Add sunglasses to the person"


Now convert this edit request:"""

        try:
            session = await HTTPClientManager.get_openai_session()
            
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": edit_system_prompt},
                        {"role": "user", "content": user_edit}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 100
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "OpenAI edit prompt error",
                        extra={"status": response.status, "error": error_text}
                    )
                    raise Exception(f"OpenAI API error: {error_text}")

                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()
        
        except Exception as e:
            logger.error("Failed to enhance edit prompt", exc_info=True)
            raise

    @staticmethod
    async def enhance_replay_prompt_with_llm(user_request: str) -> str:
        """
        АГЕНТ 4: Оптимизация промпта для replay - добавление пользователя на сгенерированное изображение.
        Использует shared ClientSession.
        """
        replay_system_prompt = """You are an expert at creating professional prompts for seamlessly integrating a person into an existing scene.


Your task: Convert user's request into a clear, professional instruction that preserves the scene while adding the person naturally.


Rules:
- Focus on NATURAL INTEGRATION of the person into the existing scene
- Preserve the scene's composition, lighting, and atmosphere
- Specify how the person should fit contextually (position, scale, interaction)
- Match lighting and perspective to the scene
- Keep it clear and actionable (2-3 sentences max)
- Always output in English
- No explanations, just the instruction


Examples:
User: "Добавь меня на эту фотографию" → "Seamlessly integrate the person into this scene, matching the existing lighting conditions and perspective. Place them naturally within the composition, ensuring realistic depth and scale."


User: "Поместите меня в этот интерьер" → "Place the person naturally in this interior space, matching the ambient lighting and room perspective. Ensure they interact believably with the environment and maintain accurate scale relative to furniture."


User: "Я хочу быть на пляже" → "Integrate the person into the beach scene, matching the golden hour lighting and ocean background. Position them naturally on the sand with appropriate shadows and reflections."


Now create integration instructions for:"""

        try:
            session = await HTTPClientManager.get_openai_session()
            
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": replay_system_prompt},
                        {"role": "user", "content": user_request}
                    ],
                    "temperature": 0.4,
                    "max_tokens": 150
                }
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "OpenAI replay prompt error",
                        extra={"status": response.status, "error": error_text}
                    )
                    raise Exception(f"OpenAI API error: {error_text}")

                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()
        
        except Exception as e:
            logger.error("Failed to enhance replay prompt", exc_info=True)
            raise

    @staticmethod
    async def generate_image_with_flux_edit(
        prompt: str,
        image_url: str = None,
        image_urls: list = None
    ) -> str:
        """
        Генерация/редактирование изображения через fal-ai API.
        Использует shared ClientSession.
        """
        if image_urls:
            endpoint = "https://fal.run/fal-ai/flux-2-pro/edit"
            payload = {
                "prompt": prompt,
                "image_urls": image_urls,
                "num_inference_steps": 40,
                "guidance_scale": 3.5,
                "num_images": 1,
                "safety_tolerance": "2"
            }
        elif image_url:
            endpoint = "https://fal.run/fal-ai/flux-2-pro/edit"
            payload = {
                "prompt": prompt,
                "image_urls": [image_url],
                "num_inference_steps": 40,
                "guidance_scale": 3.5,
                "num_images": 1,
                "safety_tolerance": "2"
            }
        else:
            endpoint = "https://fal.run/fal-ai/flux-2-pro"
            payload = {
                "prompt": prompt,
                "num_inference_steps": 40,
                "guidance_scale": 3.5,
                "num_images": 1,
                "safety_tolerance": "2"
            }

        try:
            session = await HTTPClientManager.get_fal_session()
            
            async with session.post(endpoint, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    
                    # Проверяем на content_policy_violation
                    if "content_policy_violation" in error_text.lower():
                        logger.warning(
                            "Content policy violation detected",
                            extra={
                                "prompt": payload.get("prompt", "")[:100],
                                "endpoint": endpoint
                            }
                        )
                        raise ValueError(
                            "⚠️ Запрос заблокирован системой безопасности Fal.ai\n\n"
                            "Попробуй переформулировать запрос без упоминания:\n"
                            "• Оружия\n"
                            "• Насилия\n"
                            "• Запрещенного контента\n\n"
                            "Например: вместо 'добавь топор' → 'турист с инструментом для похода'"
                        )
                    
                    logger.error(
                        "Fal.ai API error",
                        extra={
                            "status": response.status,
                            "error": error_text,
                            "endpoint": endpoint
                        }
                    )
                    raise Exception(f"Fal.ai API error: {error_text}")

                data = await response.json()
                if "images" in data and len(data["images"]) > 0:
                    return data["images"][0]["url"]

                raise Exception("Fal.ai не вернул изображение")
        
        except Exception as e:
            logger.error(
                "Failed to generate image with Fal.ai",
                exc_info=True,
                extra={"has_image_url": image_url is not None}
            )
            raise

    @staticmethod
    async def save_generation(
        session: AsyncSession,
        user_id: uuid.UUID,
        telegram_message_id: str,
        prompt: str,
        image_url: str,
        mode: str
    ) -> AIGeneration:
        """Сохранить генерацию в БД. НЕ делает commit - это сделает middleware."""
        generation = AIGeneration(
            user_id=user_id,
            telegram_message_id=telegram_message_id,
            prompt=prompt,
            image_url=image_url,
            mode=mode,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
        )
        session.add(generation)
        await session.flush()  # Получаем ID без commit
        return generation

    @staticmethod
    async def get_generation_by_message_id(
        session: AsyncSession,
        telegram_message_id: str
    ) -> AIGeneration:
        """Получить генерацию по ID сообщения"""
        result = await session.execute(
            select(AIGeneration)
            .where(AIGeneration.telegram_message_id == telegram_message_id)
            .where(AIGeneration.expires_at > datetime.now(timezone.utc))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_generations(
        session: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 10
    ) -> List[AIGeneration]:
        """Получить последние генерации пользователя"""
        result = await session.execute(
            select(AIGeneration)
            .where(AIGeneration.user_id == user_id)
            .where(AIGeneration.expires_at > datetime.now(timezone.utc))
            .order_by(AIGeneration.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_generation_by_id(
        session: AsyncSession,
        generation_id: str
    ) -> AIGeneration:
        """Получить генерацию по её ID"""
        result = await session.execute(
            select(AIGeneration)
            .where(AIGeneration.id == uuid.UUID(generation_id))
            .where(AIGeneration.expires_at > datetime.now(timezone.utc))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def process_text_to_image(
        db_session: AsyncSession,
        user_id: uuid.UUID,
        telegram_message_id: str,
        user_text: str
    ) -> Tuple[str, str]:
        """АГЕНТ 1"""
        prompt = await AIDesignerService.generate_prompt_with_openai(
            user_text,
            case_type="A"
        )

        image_url = await AIDesignerService.generate_image_with_flux_edit(prompt)

        await AIDesignerService.save_generation(
            db_session,
            user_id,
            telegram_message_id,
            prompt,
            image_url,
            "text_to_image"
        )

        return prompt, image_url

    @staticmethod
    async def process_image_edit(
        db_session: AsyncSession,
        user_id: uuid.UUID,
        telegram_message_id: str,
        reply_to_message_id: str,
        edit_text: str
    ) -> Tuple[str, str]:
        """АГЕНТ 2"""
        old_generation = await AIDesignerService.get_generation_by_message_id(
            db_session,
            reply_to_message_id
        )

        if not old_generation:
            raise ValueError("Старая генерация не найдена или истекла (48 часов)")

        edit_prompt = await AIDesignerService.enhance_edit_prompt_with_llm(edit_text)

        image_url = await AIDesignerService.generate_image_with_flux_edit(
            edit_prompt,
            image_url=old_generation.image_url
        )

        await AIDesignerService.save_generation(
            db_session,
            user_id,
            telegram_message_id,
            edit_prompt,
            image_url,
            "image_to_image_edit"
        )

        return edit_prompt, image_url

    @staticmethod
    async def process_photo_transformation(
        db_session: AsyncSession,
        user_id: uuid.UUID,
        telegram_message_id: str,
        user_photo_url: str,
        transformation_text: str
    ) -> Tuple[str, str]:
        """АГЕНТ 3"""
        transform_prompt = await AIDesignerService.generate_prompt_with_openai(
            f"Transform this image: {transformation_text}",
            case_type="C"
        )

        image_url = await AIDesignerService.generate_image_with_flux_edit(
            transform_prompt,
            image_url=user_photo_url
        )

        await AIDesignerService.save_generation(
            db_session,
            user_id,
            telegram_message_id,
            transform_prompt,
            image_url,
            "image_to_image_transform"
        )

        return transform_prompt, image_url

    @staticmethod
    async def process_replay_with_user_photo(
        db_session: AsyncSession,
        user_id: uuid.UUID,
        telegram_message_id: str,
        reply_to_message_id: str,
        user_photo_url: str,
        user_request: str
    ) -> Tuple[str, str]:
        """АГЕНТ 4: Replay через reply на сообщение"""
        original_generation = await AIDesignerService.get_generation_by_message_id(
            db_session,
            reply_to_message_id
        )

        if not original_generation:
            raise ValueError("Оригинальная генерация не найдена или истекла (48 часов)")

        # Используем общий метод
        return await AIDesignerService._process_replay_internal(
            db_session,
            user_id,
            telegram_message_id,
            original_generation,
            user_photo_url,
            user_request
        )

    @staticmethod
    async def process_replay_from_generation_id(
        db_session: AsyncSession,
        user_id: uuid.UUID,
        telegram_message_id: str,
        generation_id: str,
        user_photo_url: str,
        user_request: str
    ) -> Tuple[str, str]:
        """АГЕНТ 4: Replay через выбор из истории"""
        original_generation = await AIDesignerService.get_generation_by_id(
            db_session,
            generation_id
        )

        if not original_generation:
            raise ValueError("Выбранное изображение не найдено или истекло (48 часов)")

        # Используем общий метод
        return await AIDesignerService._process_replay_internal(
            db_session,
            user_id,
            telegram_message_id,
            original_generation,
            user_photo_url,
            user_request
        )

    @staticmethod
    async def _process_replay_internal(
        db_session: AsyncSession,
        user_id: uuid.UUID,
        telegram_message_id: str,
        original_generation: AIGeneration,
        user_photo_url: str,
        user_request: str
    ) -> Tuple[str, str]:
        """Внутренний метод для replay - общая логика"""
        replay_prompt = await AIDesignerService.enhance_replay_prompt_with_llm(user_request)

        image_url = await AIDesignerService.generate_image_with_flux_edit(
            replay_prompt,
            image_urls=[original_generation.image_url, user_photo_url]
        )

        await AIDesignerService.save_generation(
            db_session,
            user_id,
            telegram_message_id,
            replay_prompt,
            image_url,
            "image_to_image_replay"
        )

        return replay_prompt, image_url
