# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
from aiogram import types
import re
import logging

logger = logging.getLogger(__name__)


def extract_urls_with_regex(text: str) -> List[str]:
    """Извлекает URL из текста регулярными выражениями (резервный метод)"""
    if not text:
        return []

    # Паттерн для поиска URL
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,!?;:]'

    try:
        urls = re.findall(url_pattern, text, re.IGNORECASE)
        unique_urls = list(set(urls))  # Убираем дубликаты
        logger.debug(f"Найдено {len(unique_urls)} URL регулярными выражениями")
        return unique_urls
    except Exception as e:
        logger.error(f"Ошибка поиска URL регулярными выражениями: {e}")
        return []


def extract_links_from_entities(text: str, entities: Optional[List[types.MessageEntity]]) -> Dict:
    """Извлекает все ссылки из сообщения"""
    result = {
        'urls': [],
        'text_links': [],
        'mentions': [],
        'hashtags': [],
        'clean_text': text or ""
    }

    if not text:
        logger.debug("Пустой текст для извлечения ссылок")
        return result

    # Сначала извлекаем через entities
    entity_urls = set()  # Для отслеживания уже найденных URL

    if entities:
        try:
            for entity in entities:
                if entity.offset + entity.length > len(text):
                    logger.warning(
                        f"Entity выходит за пределы текста: offset={entity.offset}, length={entity.length}, text_len={len(text)}")
                    continue

                entity_text = text[entity.offset:entity.offset + entity.length]

                if entity.type == "url":
                    clean_url = entity_text.strip()
                    result['urls'].append({
                        'text': entity_text,
                        'url': clean_url
                    })
                    entity_urls.add(clean_url)
                    logger.debug(f"Найдена URL через entity: {entity_text}")

                elif entity.type == "text_link":
                    result['text_links'].append({
                        'text': entity_text,
                        'url': entity.url
                    })
                    entity_urls.add(entity.url)
                    logger.debug(f"Найдена скрытая ссылка: '{entity_text}' -> {entity.url}")

                elif entity.type == "mention":
                    result['mentions'].append({
                        'text': entity_text,
                        'username': entity_text
                    })
                    logger.debug(f"Найдено упоминание: {entity_text}")

                elif entity.type == "hashtag":
                    result['hashtags'].append({
                        'text': entity_text,
                        'hashtag': entity_text
                    })
                    logger.debug(f"Найден хештег: {entity_text}")

        except Exception as e:
            logger.error(f"Ошибка при извлечении ссылок через entities: {e}")

    # Дополнительно ищем URL регулярными выражениями
    regex_urls = extract_urls_with_regex(text)

    # Добавляем URL, которые не были найдены через entities
    for url in regex_urls:
        if url not in entity_urls:
            result['urls'].append({
                'text': url,
                'url': url
            })
            logger.debug(f"Найдена URL через regex: {url}")

    # Логируем итоговую статистику
    total_links = len(result['urls']) + len(result['text_links'])
    logger.info(
        f"Извлечено ссылок: {len(result['urls'])} обычных + {len(result['text_links'])} скрытых = {total_links} всего")

    return result


def format_links_for_ai(links_data: Dict) -> str:
    """Форматирует ссылки для отправки в AI"""
    formatted_links = []

    # Обычные URL
    for idx, url_data in enumerate(links_data['urls'], 1):
        formatted_links.append(f"URL #{idx}: {url_data['url']}")

    # Скрытые ссылки (текстовые ссылки)
    for idx, link_data in enumerate(links_data['text_links'], 1):
        formatted_links.append(f"Текстовая ссылка #{idx}: '{link_data['text']}' -> {link_data['url']}")

    # Упоминания пользователей
    for mention_data in links_data['mentions']:
        formatted_links.append(f"Упоминание пользователя: {mention_data['username']}")

    # Хештеги
    for hashtag_data in links_data['hashtags']:
        formatted_links.append(f"Хештег: {hashtag_data['hashtag']}")

    if formatted_links:
        result = "\n".join(formatted_links)
        logger.info(f"Отформатировано {len(formatted_links)} ссылок/упоминаний для AI")
        return result
    else:
        logger.debug("Ссылки и упоминания не найдены")
        return "Ссылки и упоминания не найдены"


def validate_html_links(text: str) -> bool:
    """Проверяет корректность HTML ссылок в тексте"""
    try:
        # Находим все HTML ссылки
        html_link_pattern = r'<a\s+href=[\"\']([^\"\']+)[\"\'][^>]*>([^<]+)</a>'
        links = re.findall(html_link_pattern, text, re.IGNORECASE)

        if links:
            logger.info(f"Найдено {len(links)} HTML ссылок в обработанном тексте:")
            for idx, (url, link_text) in enumerate(links, 1):
                logger.info(f"  #{idx}: '{link_text}' -> {url}")
            return True
        else:
            logger.warning("HTML ссылки в обработанном тексте не найдены")
            return False

    except Exception as e:
        logger.error(f"Ошибка валидации HTML ссылок: {e}")
        return False


def debug_links_extraction(text: str, entities: Optional[List[types.MessageEntity]]) -> None:
    """Отладочная функция для проверки извлечения ссылок"""
    logger.info("=== ОТЛАДКА ИЗВЛЕЧЕНИЯ ССЫЛОК ===")
    logger.info(f"Длина текста: {len(text) if text else 0}")
    logger.info(f"Количество entities: {len(entities) if entities else 0}")

    if entities:
        for idx, entity in enumerate(entities):
            logger.info(f"Entity #{idx}: type={entity.type}, offset={entity.offset}, length={entity.length}")
            if hasattr(entity, 'url'):
                logger.info(f"  -> URL: {entity.url}")

    # Проверяем regex поиск
    regex_urls = extract_urls_with_regex(text)
    logger.info(f"Regex нашел {len(regex_urls)} URL: {regex_urls}")

    logger.info("=== КОНЕЦ ОТЛАДКИ ===")


def remove_telegram_links(text: str) -> str:
    """Удаляет ссылки на Telegram из текста"""
    if not text:
        return text

    # Паттерны для Telegram ссылок
    telegram_patterns = [
        r'https?://t\.me/[^\s<>"\'\)]+',
        r'https?://telegram\.me/[^\s<>"\'\)]+',
        r'tg://[^\s<>"\'\)]+',
        r'@[a-zA-Z0-9_]+',  # Упоминания
    ]

    cleaned_text = text
    for pattern in telegram_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)

    # Очищаем лишние пробелы
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return cleaned_text