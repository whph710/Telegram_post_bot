# -*- coding: utf-8 -*-
import asyncio
import logging
import re
import os
from typing import Optional
from openai import AsyncOpenAI
from config import DEEPSEEK

logger = logging.getLogger(__name__)


async def load_prompt(filename: str = 'prompt.txt') -> str:
    """Загружает промпт из файла с обработкой кодировок"""
    if not os.path.exists(filename):
        logger.warning(f"Файл {filename} не найден, используется стандартный промпт")
        return get_default_prompt()

    # Пробуем разные кодировки
    encodings = ['utf-8', 'cp1251', 'windows-1251', 'iso-8859-1']

    for encoding in encodings:
        try:
            with open(filename, 'r', encoding=encoding) as f:
                content = f.read().strip()
                logger.info(f"Промпт загружен из {filename} (кодировка: {encoding})")
                return content
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            logger.error(f"Ошибка при чтении {filename}: {e}")
            continue

    logger.error(f"Не удалось прочитать {filename} ни в одной кодировке")
    return get_default_prompt()


def get_default_prompt() -> str:
    """Возвращает стандартный промпт"""
    return """Ты опытный копирайтер и редактор контента. 
Переработай присланный текст, сохранив основную суть, но улучшив читабельность и структуру.

ВАЖНО: 
- Все ссылки должны быть сохранены и оформлены в HTML формате с тегом <a href="URL">текст</a>
- Если в тексте есть упоминания (@username), сохрани их как есть
- Ответ должен быть в обычном тексте с HTML-ссылками, БЕЗ тегов <p>, <div>, <html>, <!doctype> и других структурных тегов
- Используй только теги <a>, <b>, <i>, <u>, <s>, <code>, <pre>
- Сохрани смысл и тон исходного сообщения
- Улучши структуру и читабельность"""


def clean_html_for_telegram(text: str) -> str:
    """Очищает HTML от неподдерживаемых Telegram тегов"""
    if not text:
        return ""

    # Удаляем структурные HTML теги
    unwanted_patterns = [
        r'<!DOCTYPE[^>]*>',
        r'</?html[^>]*>',
        r'</?head[^>]*>',
        r'</?body[^>]*>',
        r'</?div[^>]*>',
        r'</?p[^>]*>',
        r'</?span[^>]*>',
        r'</?section[^>]*>',
        r'</?article[^>]*>',
        r'</?header[^>]*>',
        r'</?footer[^>]*>',
        r'</?main[^>]*>',
        r'</?nav[^>]*>',
        r'</?aside[^>]*>',
        r'</?h[1-6][^>]*>',
        r'</h[1-6]>',
        r'</?ul[^>]*>',
        r'</?ol[^>]*>',
        r'</?li[^>]*>',
        r'</?br[^>]*/?>'
    ]

    cleaned_text = text
    for pattern in unwanted_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)

    # Нормализация пробелов
    cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
    cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)
    cleaned_text = cleaned_text.strip()

    # Проверка разрешенных тегов
    allowed_pattern = r'</?(?:a|b|i|u|s|code|pre)(?:\s[^>]*)?>'

    # Удаляем неразрешенные теги
    all_tags = re.findall(r'<[^>]+>', cleaned_text)
    for tag in all_tags:
        if not re.match(allowed_pattern, tag, re.IGNORECASE):
            cleaned_text = cleaned_text.replace(tag, '')
            logger.warning(f"Удален неподдерживаемый тег: {tag}")

    return cleaned_text


async def validate_deepseek_connection() -> bool:
    """Проверяет подключение к DeepSeek API"""
    if not DEEPSEEK:
        logger.error("DEEPSEEK API ключ не найден в конфигурации")
        return False

    try:
        client = AsyncOpenAI(
            api_key=DEEPSEEK,
            base_url="https://api.deepseek.com",
            timeout=10.0
        )

        # Тестовый запрос
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )

        logger.info("Соединение с DeepSeek API успешно")
        return True

    except Exception as e:
        logger.error(f"Ошибка подключения к DeepSeek API: {e}")
        return False


async def process_with_deepseek(text: str, links: str, prompt_file: str = 'prompt.txt') -> str:
    """Обрабатывает текст через DeepSeek AI"""
    if not text.strip():
        logger.warning("Пустой текст для обработки")
        return ""

    # Проверяем соединение
    if not await validate_deepseek_connection():
        return f"Ошибка подключения к AI. Исходный текст:\n{text}"

    try:
        prompt = await load_prompt(prompt_file)

        user_content = f"""
Текст для обработки:
{text}

Найденные ссылки и упоминания:
{links}

Переработай этот контент согласно инструкциям в системном промпте.
Обязательно сохрани все ссылки в правильном HTML формате.
ВАЖНО: НЕ используй теги <p>, <div>, <html>, <!doctype> и другие структурные теги!
Используй только теги: <a>, <b>, <i>, <u>, <s>, <code>, <pre>
"""

        client = AsyncOpenAI(
            api_key=DEEPSEEK,
            base_url="https://api.deepseek.com",
            timeout=30.0
        )

        logger.info(f"Отправляем запрос в DeepSeek (длина текста: {len(text)} символов)")

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
        cleaned_result = clean_html_for_telegram(result)

        logger.info(f"AI обработка завершена успешно (результат: {len(cleaned_result)} символов)")
        return cleaned_result

    except Exception as e:
        logger.error(f"Ошибка AI обработки: {e}")
        return f"Ошибка обработки ИИ: {str(e)}\n\nИсходный текст:\n{text}"