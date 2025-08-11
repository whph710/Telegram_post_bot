# -*- coding: utf-8 -*-
import asyncio
import logging
import re
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
- Ответ должен быть в обычном тексте с HTML-ссылками, БЕЗ тегов <p>, <div>, <html>, <!doctype> и других структурных тегов
- Используй только теги <a>, <b>, <i>, <u>, <s>, <code>, <pre>
- Сохрани смысл и тон исходного сообщения
- Улучши структуру и читабельность"""


def clean_html_for_telegram(text: str) -> str:
    """Очищает HTML от неподдерживаемых Telegram тегов"""
    if not text:
        return ""

    # Удаляем структурные HTML теги, которые Telegram не поддерживает
    unwanted_tags = [
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
    for pattern in unwanted_tags:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)

    # Убираем лишние пробелы и переносы строк
    cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)  # Двойные переносы оставляем
    cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)  # Множественные пробелы в один
    cleaned_text = cleaned_text.strip()

    # Проверяем, что остались только разрешенные теги
    allowed_tags = r'</?(?:a|b|i|u|s|code|pre)(?:\s[^>]*)?>|<a\s+href=["\'][^"\']*["\'][^>]*>'

    # Находим все теги
    all_tags = re.findall(r'<[^>]+>', cleaned_text)

    # Удаляем неразрешенные теги
    for tag in all_tags:
        if not re.match(allowed_tags, tag, re.IGNORECASE):
            cleaned_text = cleaned_text.replace(tag, '')
            logger.warning(f"⚠️ Удален неподдерживаемый тег: {tag}")

    return cleaned_text


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
ВАЖНО: НЕ используй теги <p>, <div>, <html>, <!doctype> и другие структурные теги!
Используй только теги: <a>, <b>, <i>, <u>, <s>, <code>, <pre>
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

        # Очищаем результат от неподдерживаемых тегов
        cleaned_result = clean_html_for_telegram(result)

        logger.info(f"✅ AI обработка завершена успешно (результат: {len(cleaned_result)} символов)")

        return cleaned_result

    except Exception as e:
        logger.error(f"❌ Ошибка AI обработки: {e}")
        # В случае ошибки возвращаем исходный текст с предупреждением
        return f"⚠️ Ошибка обработки ИИ: {str(e)}\n\nИсходный текст:\n{text}"