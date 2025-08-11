# -*- coding: utf-8 -*-
from typing import List, Dict, Optional
from aiogram import types
import re


def extract_links_from_entities(text: str, entities: Optional[List[types.MessageEntity]]) -> Dict:
    """Извлекает все ссылки из сообщения"""
    result = {
        'urls': [],
        'text_links': [],
        'mentions': [],
        'clean_text': text or ""
    }

    if not entities or not text:
        return result

    for entity in entities:
        entity_text = text[entity.offset:entity.offset + entity.length]

        if entity.type == "url":
            result['urls'].append({
                'text': entity_text,
                'url': entity_text
            })
        elif entity.type == "text_link":
            result['text_links'].append({
                'text': entity_text,
                'url': entity.url
            })
        elif entity.type == "mention":
            result['mentions'].append({
                'text': entity_text,
                'username': entity_text
            })

    return result


def format_links_for_ai(links_data: Dict) -> str:
    """Форматирует ссылки для отправки в AI"""
    formatted_links = []

    # Обычные URL
    for url_data in links_data['urls']:
        formatted_links.append(f"URL: {url_data['url']}")

    # Скрытые ссылки
    for link_data in links_data['text_links']:
        formatted_links.append(f"Скрытая ссылка: '{link_data['text']}' -> {link_data['url']}")

    # Упоминания
    for mention_data in links_data['mentions']:
        formatted_links.append(f"Упоминание: {mention_data['username']}")

    return "\n".join(formatted_links) if formatted_links else "Ссылки не найдены"