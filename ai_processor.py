# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Optional
from openai import AsyncOpenAI
from config import DEEPSEEK

logger = logging.getLogger(__name__)


async def load_prompt() -> str:
    """Загружает промпт из файла с автоопределением кодировки"""
    try:
        # Сначала пытаемся UTF-8
        try:
            with open('prompt.txt', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                logger.info("✅ Промпт загружен из файла (UTF-8)")
                return content
        except UnicodeDecodeError:
            # Если не получилось, пробуем CP1251 (Windows)
            with open('prompt.txt', 'r', encoding='cp1251') as f:
                content = f.read().strip()
                logger.info("✅ Промпт загружен из файла (CP1251)")
                return content
    except FileNotFoundError:
        logger.warning("⚠️ prompt.txt не найден, используется стандартный промпт")
        return """Ты опытный копирайтер и редактор контента. 
Переработай присланный текст, сохранив основную суть, но улучшив читабельность и структуру.

ВАЖНО: 
- Все ссылки должны быть сохранены и оформлены в HTML формате с тегом <a href="URL">текст</a>
- Если в тексте есть упоминания (@username), сохрани их как есть
- Ответ должен быть в формате HTML с кликабельными ссылками
- Сохрани смысл и тон исходного сообщения
- Улучши структуру и читабельность"""


async def process_with_deepseek(text: str, links: str) -> str:
    """Обрабатывает текст через DeepSeek AI"""
    if not text.strip():
        logger.warning("⚠️ Пустой текст для обработки")
        return ""

    try:
        prompt = await load_prompt()

        # Формируем запрос
        user_content = f"""
Текст для обработки:
{text}

Найденные ссылки и упоминания:
{links}

Переработай этот контент согласно инструкциям в системном промпте.
Обязательно сохрани все ссылки в правильном HTML формате.
"""

        client = AsyncOpenAI(
            api_key=DEEPSEEK,
            base_url="https://api.deepseek.com"
        )

        logger.info(f"🤖 Отправляем запрос в DeepSeek (длина текста: {len(text)} символов)")

        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=4000,
            temperature=0.7
        )

        result = response.choices[0].message.content.strip()
        logger.info(f"✅ AI обработка завершена успешно (результат: {len(result)} символов)")

        return result

    except Exception as e:
        logger.error(f"❌ Ошибка AI обработки: {e}")
        # В случае ошибки возвращаем исходный текст с предупреждением
        return f"⚠️ Ошибка обработки ИИ: {str(e)}\n\nИсходный текст:\n{text}"