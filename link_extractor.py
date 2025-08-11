# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
from aiogram import types
import re
import logging

logger = logging.getLogger(__name__)


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

    if not entities:
        logger.debug("Нет entities для обработки")
        return result

    try:
        for entity in entities:
            if entity.offset + entity.length > len(text):
                logger.warning(
                    f"Entity выходит за пределы текста: offset={entity.offset}, length={entity.length}, text_len={len(text)}")
                continue

            entity_text = text[entity.offset:entity.offset + entity.length]

            if entity.type == "url":
                result['urls'].append({
                    'text': entity_text,
                    'url': entity_text.strip()
                })
                logger.debug(f"Найдена URL: {entity_text}")

            elif entity.type == "text_link":
                result['text_links'].append({
                    'text': entity_text,
                    'url': entity.url
                })
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
        logger.error(f"Ошибка при извлечении ссылок: {e}")

    return result


def format_links_for_ai(links_data: Dict) -> str:
    """Форматирует ссылки для отправки в AI"""
    formatted_links = []

    # Обычные URL
    for url_data in links_data['urls']:
        formatted_links.append(f"URL: {url_data['url']}")

    # Скрытые ссылки (текстовые ссылки)
    for link_data in links_data['text_links']:
        formatted_links.append(f"Текстовая ссылка: '{link_data['text']}' -> {link_data['url']}")

    # Упоминания пользователей
    for mention_data in links_data['mentions']:
        formatted_links.append(f"Упоминание пользователя: {mention_data['username']}")

    # Хештеги
    for hashtag_data in links_data['hashtags']:
        formatted_links.append(f"Хештег: {hashtag_data['hashtag']}")

    if formatted_links:
        result = "\n".join(formatted_links)
        logger.info(f"Отформатировано {len(formatted_links)} ссылок/упоминаний")
        return result
    else:
        logger.debug("Ссылки и упоминания не найдены")
        return "Ссылки и упоминания не найдены"


def validate_html_links(text: str) -> bool:
    """Проверяет корректность HTML ссылок в тексте"""
    try:
        # Простая проверка на наличие корректных HTML ссылок
        html_link_pattern = r'<a\s+href=[\"\']([^\"\']+)[\"\'][^>]*>([^<]+)</a>'
        links = re.findall(html_link_pattern, text, re.IGNORECASE)

        if links:
            logger.info(f"Найдено {len(links)} HTML ссылок в обработанном тексте")
            return True
        return False

    except Exception as e:
        logger.error(f"Ошибка валидации HTML ссылок: {e}")
        return False