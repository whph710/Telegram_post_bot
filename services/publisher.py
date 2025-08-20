# -*- coding: utf-8 -*-
import logging
from typing import Dict, Any
from config import GROUP_ID
from services.media_handler import MediaProcessor

logger = logging.getLogger(__name__)
media_processor = MediaProcessor()


async def publish_post_now(post_data: Dict[str, Any]) -> bool:
    """Публикует пост немедленно"""
    try:
        from bot import bot
        processed_text = post_data['processed_text']

        if post_data.get('original_messages'):
            # Альбом
            messages = post_data['original_messages']
            media_group = media_processor.build_media_group(messages, processed_text)

            await bot.send_media_group(
                chat_id=GROUP_ID,
                media=media_group.build()
            )
            logger.info(f"Альбом опубликован (пост #{post_data.get('id', 'unknown')})")

        elif post_data.get('original_message'):
            # Одиночное сообщение
            await _publish_single_message(post_data['original_message'], processed_text)
            logger.info(f"Одиночное сообщение опубликовано (пост #{post_data.get('id', 'unknown')})")

        else:
            # Только текст
            if processed_text.strip():
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=processed_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                logger.info(f"Текстовый пост опубликован (пост #{post_data.get('id', 'unknown')})")

        return True

    except Exception as e:
        logger.error(f"Ошибка публикации поста #{post_data.get('id', 'unknown')}: {e}")
        return False


async def _publish_single_message(message, processed_text: str):
    """Публикует одиночное сообщение"""
    from bot import bot

    media_info = media_processor.extract_media_info(message)

    if media_info['has_media']:
        if media_info['type'] in ['photo', 'video', 'document']:
            # Используем медиа-группу для единообразия
            media_group = media_processor.build_single_media_group(message, processed_text)
            await bot.send_media_group(
                chat_id=GROUP_ID,
                media=media_group.build()
            )

        elif media_info['type'] == 'animation':
            await bot.send_animation(
                chat_id=GROUP_ID,
                animation=media_info['file_id'],
                caption=processed_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

        elif media_info['type'] == 'voice':
            await bot.send_voice(
                chat_id=GROUP_ID,
                voice=media_info['file_id'],
                caption=processed_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

        elif media_info['type'] == 'video_note':
            # Кружочки не поддерживают caption
            await bot.send_video_note(
                chat_id=GROUP_ID,
                video_note=media_info['file_id']
            )
            # Отправляем текст отдельно
            if processed_text.strip():
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=processed_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
    else:
        # Только текст
        if processed_text.strip():
            await bot.send_message(
                chat_id=GROUP_ID,
                text=processed_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )