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

        # Проверяем GROUP_ID
        if not GROUP_ID:
            logger.error("GROUP_ID не настроен")
            return False

        logger.info(f"Публикуем пост #{post_data.get('id', 'unknown')} в группу {GROUP_ID}")

        if post_data.get('original_messages'):
            # Альбом
            messages = post_data['original_messages']
            logger.info(f"Публикуем альбом из {len(messages)} элементов")

            # Получаем информацию о первом медиа для подписи
            first_message = messages[0]
            media_info = media_processor.extract_media_info(first_message)

            if media_info['type'] == 'photo':
                # ИСПРАВЛЕНО: убираем disable_web_page_preview для send_photo
                await bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=media_info['file_id'],
                    caption=processed_text,
                    parse_mode="HTML"
                )
            elif media_info['type'] == 'video':
                # ИСПРАВЛЕНО: убираем disable_web_page_preview для send_video
                await bot.send_video(
                    chat_id=GROUP_ID,
                    video=media_info['file_id'],
                    caption=processed_text,
                    parse_mode="HTML"
                )
            else:
                # Для других типов - сначала текст, потом медиа
                if processed_text.strip():
                    await bot.send_message(
                        chat_id=GROUP_ID,
                        text=processed_text,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )

                # Отправляем первое медиа
                await _send_single_media(first_message, "")

            logger.info(f"Альбом опубликован (пост #{post_data.get('id', 'unknown')})")

        elif post_data.get('original_message'):
            # Одиночное сообщение
            message = post_data['original_message']
            await _send_single_media(message, processed_text)
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


async def _send_single_media(message, caption: str):
    """Отправляет одиночное медиа"""
    from bot import bot

    media_info = media_processor.extract_media_info(message)

    if not media_info['has_media']:
        # Только текст
        if caption.strip():
            await bot.send_message(
                chat_id=GROUP_ID,
                text=caption,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        return

    try:
        if media_info['type'] == 'photo':
            # ИСПРАВЛЕНО: убираем disable_web_page_preview для send_photo
            await bot.send_photo(
                chat_id=GROUP_ID,
                photo=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )

        elif media_info['type'] == 'video':
            # ИСПРАВЛЕНО: убираем disable_web_page_preview для send_video
            await bot.send_video(
                chat_id=GROUP_ID,
                video=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )

        elif media_info['type'] == 'document':
            # ИСПРАВЛЕНО: убираем disable_web_page_preview для send_document
            await bot.send_document(
                chat_id=GROUP_ID,
                document=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )

        elif media_info['type'] == 'animation':
            # ИСПРАВЛЕНО: убираем disable_web_page_preview для send_animation
            await bot.send_animation(
                chat_id=GROUP_ID,
                animation=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )

        elif media_info['type'] == 'voice':
            # ИСПРАВЛЕНО: убираем disable_web_page_preview для send_voice
            await bot.send_voice(
                chat_id=GROUP_ID,
                voice=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )

        elif media_info['type'] == 'video_note':
            # Кружочки не поддерживают caption
            await bot.send_video_note(
                chat_id=GROUP_ID,
                video_note=media_info['file_id']
            )
            # Отправляем текст отдельно
            if caption.strip():
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=caption,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )

        else:
            logger.warning(f"Неподдерживаемый тип медиа: {media_info['type']}")
            # Отправляем как текст
            if caption.strip():
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=caption,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )

    except Exception as e:
        logger.error(f"Ошибка отправки медиа типа {media_info['type']}: {e}")
        # Пытаемся отправить хотя бы текст
        if caption.strip():
            try:
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=f"Ошибка отправки медиа. Текст поста:\n\n{caption}",
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            except:
                logger.error("Не удалось отправить даже текст")