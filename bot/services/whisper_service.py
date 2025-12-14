"""
Whisper Service для транскрибации голосовых сообщений
Использует OpenAI Whisper API
"""

import os
import logging
from typing import Optional, List
from openai import AsyncOpenAI
import aiohttp
from aiogram import Bot

logger = logging.getLogger(__name__)


class WhisperService:
    """Сервис для транскрибации голосовых сообщений через Whisper API"""
    
    def __init__(self):
        self.api_key = os.getenv('OPEN_AI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OPEN_AI_API_KEY не найден в .env")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini-transcribe"
        
        logger.info("Whisper Service инициализирован")
    
    async def transcribe_voice(
        self,
        bot: Bot,
        file_id: str,
        language: str = "ru"
    ) -> str:
        """
        Транскрибация голосового сообщения
        
        Args:
            bot: Экземпляр бота для скачивания файла
            file_id: ID файла в Telegram
            language: Язык транскрипции (по умолчанию русский)
        
        Returns:
            str: Транскрибированный текст
        """
        temp_file_path = None
        
        try:
            # Получаем информацию о файле
            file = await bot.get_file(file_id)
            
            # Скачиваем файл
            temp_file_path = f"/tmp/voice_{file_id}.ogg"
            await bot.download_file(file.file_path, destination=temp_file_path)
            
            logger.info(f"Голосовой файл скачан: {temp_file_path}")
            
            # Транскрибируем через Whisper API
            with open(temp_file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    response_format="text"
                )
            
            logger.info(f"Транскрипция выполнена успешно (length: {len(transcript)} chars)")
            
            return transcript
            
        except Exception as e:
            logger.error(f"Ошибка при транскрибации голосового сообщения: {e}", exc_info=True)
            raise
        
        finally:
            # Удаляем временный файл
            if temp_file_path:
                try:
                    import os as os_module
                    if os_module.path.exists(temp_file_path):
                        os_module.remove(temp_file_path)
                        logger.debug(f"Временный файл удален: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временный файл: {e}")
    
    async def transcribe_multiple_voices(
        self,
        bot: Bot,
        file_ids: List[str],
        language: str = "ru"
    ) -> str:
        """
        Транскрибация нескольких голосовых сообщений и объединение в один текст
        
        Args:
            bot: Экземпляр бота
            file_ids: Список ID файлов в Telegram
            language: Язык транскрипции
        
        Returns:
            str: Объединенный транскрибированный текст
        """
        try:
            transcripts = []
            
            for idx, file_id in enumerate(file_ids, 1):
                logger.info(f"Транскрибация голосового фрагмента {idx}/{len(file_ids)}")
                transcript = await self.transcribe_voice(bot, file_id, language)
                transcripts.append(transcript)
            
            # Объединяем все транскрипты
            combined_text = " ".join(transcripts)
            
            logger.info(f"Все голосовые сообщения транскрибированы. Общая длина: {len(combined_text)} символов")
            
            return combined_text
            
        except Exception as e:
            logger.error(f"Ошибка при транскрибации нескольких голосовых: {e}", exc_info=True)
            raise


# Singleton инстанс
_whisper_service_instance: Optional[WhisperService] = None


def get_whisper_service() -> WhisperService:
    """Получить singleton инстанс Whisper сервиса"""
    global _whisper_service_instance
    
    if _whisper_service_instance is None:
        _whisper_service_instance = WhisperService()
    
    return _whisper_service_instance