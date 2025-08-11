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
                return f.read().strip()
        except UnicodeDecodeError:
            # Если не получилось, пробуем CP1251 (Windows)
            with open('prompt.txt', 'r', encoding='cp1251') as f:
                return f.read().strip()
    except FileNotFoundError:
        logger.warning("prompt.txt не найден, используется стандартный промпт")
        return """Ты опытный копирайтер и редактор контента. 
Переработай присланный текст, сохранив основную суть, но улучшив читабельность.
Все ссылки должны быть оформлены в HTML формате с тегом <a href="URL">текст</a>.
Ответ должен быть в формате HTML с кликабельными ссылками."""

async def process_with_deepseek(text: str, links: str) -> str:
    """Обрабатывает текст через DeepSeek AI"""
    try:
        prompt = await load_prompt()

        # Формируем запрос
        user_content = f"""
Текст для обработки:
{text}

Найденные ссылки:
{links}

Переработай этот контент согласно инструкциям в промпте.
"""

        client = AsyncOpenAI(
            api_key=DEEPSEEK,
            base_url="https://api.deepseek.com"
        )

        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=3000,
            temperature=0.7
        )

        result = response.choices[0].message.content
        logger.info(f"✅ AI обработка завершена: {len(result)} символов")
        return result

    except Exception as e:
        logger.error(f"❌ Ошибка AI обработки: {e}")
        return f"Ошибка обработки текста: {str(e)}"