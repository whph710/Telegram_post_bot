# -*- coding: utf-8 -*-
import asyncio
import logging
import re
import os
from typing import Optional
from openai import AsyncOpenAI
from config import (
    DEEPSEEK_API_KEY, SETTINGS, PROMPT_PATHS, MESSAGES
)

logger = logging.getLogger(__name__)


class AIProcessor:
    """Класс для обработки текста через ИИ"""

    def __init__(self):
        self.client = None
        self._prompts_cache = {}

    async def _get_client(self) -> Optional[AsyncOpenAI]:
        """Получает клиента OpenAI"""
        if not self.client:
            if not DEEPSEEK_API_KEY:
                logger.error("DEEPSEEK API ключ не найден в конфигурации")
                return None

            self.client = AsyncOpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=SETTINGS['deepseek_base_url'],
                timeout=SETTINGS['ai_request_timeout']
            )

        return self.client

    async def load_prompt(self, prompt_type: str) -> str:
        """Загружает промпт из файла с кешированием"""
        if prompt_type in self._prompts_cache:
            return self._prompts_cache[prompt_type]

        filename = PROMPT_PATHS.get(prompt_type)
        if not filename:
            logger.warning(f"Неизвестный тип промпта: {prompt_type}")
            return self._get_default_prompt(prompt_type)

        if not os.path.exists(filename):
            logger.warning(f"Файл промпта {filename} не найден, используется стандартный")
            return self._get_default_prompt(prompt_type)

        # Пробуем разные кодировки
        encodings = ['utf-8', 'cp1251', 'windows-1251', 'iso-8859-1']

        for encoding in encodings:
            try:
                with open(filename, 'r', encoding=encoding) as f:
                    content = f.read().strip()
                    logger.info(f"Промпт загружен из {filename} (кодировка: {encoding})")
                    self._prompts_cache[prompt_type] = content
                    return content
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.error(f"Ошибка при чтении {filename}: {e}")
                continue

        logger.error(f"Не удалось прочитать {filename} ни в одной кодировке")
        return self._get_default_prompt(prompt_type)

    def _get_default_prompt(self, prompt_type: str) -> str:
        """Возвращает стандартный промпт для типа"""
        defaults = {
            'style_formatting': """Ты опытный копирайтер и редактор контента. 
Переработай присланный текст, сохранив основную суть, но улучшив читабельность и структуру.

ВАЖНО: 
- Все ссылки должны быть сохранены и оформлены в HTML формате с тегом <a href="URL">текст</a>
- Если в тексте есть упоминания (@username), сохрани их как есть
- Ответ должен быть в обычном тексте с HTML-ссылками, БЕЗ тегов <p>, <div>, <html>, <!doctype> и других структурных тегов
- Используй только теги <a>, <b>, <i>, <u>, <s>, <code>, <pre>
- Сохрани смысл и тон исходного сообщения
- Улучши структуру и читабельность""",

            'group_processing': """Ты опытный копирайтер для Telegram-канала.
Обработай текст для публикации в группе:

ВАЖНО:
- УДАЛИ все упоминания @username и ссылки на Telegram-каналы (t.me, telegram.me)
- Сохрани только внешние ссылки (не Telegram) в формате <a href="URL">текст</a>
- Добавь подпись канала в конце
- Форматируй для группы, улучши читабельность
- Используй только теги <a>, <b>, <i>, <u>, <s>, <code>, <pre>""",

            'post_improvement': """Ты опытный копирайтер и редактор контента.
Тебе предоставлен основной пост и дополнительная информация для его доработки.

Задача: Интегрируй дополнительную информацию в основной пост, улучшив его структуру и читабельность.

ВАЖНЫЕ ПРАВИЛА:
- Все ссылки должны быть сохранены и оформлены в HTML формате с тегом <a href="URL">текст</a>
- Упоминания (@username) сохрани как есть
- Используй ТОЛЬКО теги: <a>, <b>, <i>, <u>, <s>, <code>, <pre>
- Дополнительную информацию органично встрой в текст, не дублируй содержимое
- Сохрани смысл и тон исходного сообщения
- Улучши структуру и читабельность финального поста"""
        }

        return defaults.get(prompt_type, defaults['style_formatting'])

    def clean_html_for_telegram(self, text: str) -> str:
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

        # Исправляем незакрытые теги
        cleaned_text = self._fix_unclosed_tags(cleaned_text)

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

    def _fix_unclosed_tags(self, text: str) -> str:
        """Исправляет незакрытые теги"""
        # Находим все открывающие теги
        open_tags = re.findall(r'<(b|i|u|s|code)(?:\s[^>]*)?>', text, re.IGNORECASE)
        close_tags = re.findall(r'</(b|i|u|s|code)>', text, re.IGNORECASE)

        # Подсчитываем теги
        from collections import Counter
        open_count = Counter([tag.lower() for tag in open_tags])
        close_count = Counter([tag.lower() for tag in close_tags])

        # Добавляем недостающие закрывающие теги
        for tag, count in open_count.items():
            missing = count - close_count.get(tag, 0)
            if missing > 0:
                for _ in range(missing):
                    text += f'</{tag}>'
                logger.info(f"Добавлен недостающий закрывающий тег: </{tag}>")

        # Удаляем лишние закрывающие теги
        for tag, count in close_count.items():
            excess = count - open_count.get(tag, 0)
            if excess > 0:
                # Удаляем лишние закрывающие теги с конца
                for _ in range(excess):
                    pattern = f'</{tag}>'
                    pos = text.rfind(pattern)
                    if pos != -1:
                        text = text[:pos] + text[pos + len(pattern):]
                        logger.info(f"Удален лишний закрывающий тег: </{tag}>")

        return text

    def validate_telegram_html(self, text: str) -> str:
        """Валидация HTML для Telegram API"""
        if not text:
            return ""

        # Проверяем длину текста
        if len(text) > 4096:
            logger.warning(f"Текст слишком длинный ({len(text)} символов), обрезаем до 4096")
            text = text[:4093] + "..."

        # Проверяем корректность HTML
        try:
            # Простая проверка на корректность HTML тегов
            import xml.etree.ElementTree as ET
            # Оборачиваем в корневой элемент для проверки
            test_xml = f"<root>{text}</root>"
            ET.fromstring(test_xml)
            return text
        except ET.ParseError as e:
            logger.warning(f"Некорректный HTML, исправляем: {e}")
            return self.clean_html_for_telegram(text)

    async def validate_connection(self) -> bool:
        """Проверяет подключение к DeepSeek API"""
        client = await self._get_client()
        if not client:
            return False

        try:
            response = await client.chat.completions.create(
                model=SETTINGS['deepseek_model'],
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            logger.info("Соединение с DeepSeek API успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к DeepSeek API: {e}")
            return False

    async def process_text(self, text: str, links: str, prompt_type: str = 'style_formatting') -> str:
        """Обрабатывает текст через DeepSeek AI"""
        if not text.strip():
            logger.warning("Пустой текст для обработки")
            return ""

        # Проверяем соединение
        client = await self._get_client()
        if not client:
            return f"{MESSAGES.get('ai_processing_error', 'Ошибка ИИ')}. Исходный текст:\n{text}"

        try:
            # Загружаем промпт
            system_prompt = await self.load_prompt(prompt_type)

            # Формируем пользовательский запрос
            user_content = f"""
Текст для обработки:
{text}

Найденные ссылки и упоминания:
{links}

Переработай этот контент согласно инструкциям в системном промпте.
Обязательно сохрани все ссылки в правильном HTML формате.
ВАЖНО: НЕ используй теги <p>, <div>, <html>, <!doctype> и другие структурные теги!
Используй только теги: <a>, <b>, <i>, <u>, <s>, <code>, <pre>
ОБЯЗАТЕЛЬНО закрывай все открытые теги!
"""

            logger.info(f"Отправляем запрос в DeepSeek (тип: {prompt_type}, длина: {len(text)} символов)")

            response = await client.chat.completions.create(
                model=SETTINGS['deepseek_model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=SETTINGS['ai_max_tokens'],
                temperature=SETTINGS['ai_temperature']
            )

            result = response.choices[0].message.content.strip()
            cleaned_result = self.clean_html_for_telegram(result)
            validated_result = self.validate_telegram_html(cleaned_result)

            logger.info(f"AI обработка завершена успешно (результат: {len(validated_result)} символов)")
            return validated_result

        except Exception as e:
            logger.error(f"Ошибка AI обработки: {e}")
            return f"{MESSAGES.get('ai_processing_error', 'Ошибка ИИ')}: {str(e)}\n\nИсходный текст:\n{text}"

    def clear_cache(self):
        """Очищает кеш промптов"""
        self._prompts_cache.clear()
        logger.info("Кеш промптов очищен")

    async def save_prompt(self, prompt_type: str, content: str) -> bool:
        """Сохраняет промпт в файл"""
        filename = PROMPT_PATHS.get(prompt_type)
        if not filename:
            logger.error(f"Неизвестный тип промпта: {prompt_type}")
            return False

        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

            # Обновляем кеш
            self._prompts_cache[prompt_type] = content

            logger.info(f"Промпт {prompt_type} сохранен в {filename}")
            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения промпта {prompt_type}: {e}")
            return False


# Глобальный экземпляр процессора
ai_processor = AIProcessor()


# Функция-обертка для совместимости
async def process_with_ai(text: str, links: str, prompt_type: str = 'style_formatting') -> str:
    """Обертка для обработки текста через ИИ"""
    return await ai_processor.process_text(text, links, prompt_type)