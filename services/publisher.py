# -*- coding: utf-8 -*-
import logging
from typing import Dict, Any
from config import GROUP_ID
from services.media_handler import MediaProcessor

logger = logging.getLogger(__name__)
media_processor = MediaProcessor()


async def publish_post_now(post_data: Dict[str, Any]) -> bool:
    """Публикует пост немедленно с повторными попытками"""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            success = await _publish_post_attempt(post_data)
            if success:
                return True

            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                logger.info(f"Повторная попытка публикации #{attempt + 2}")

        except Exception as e:
            logger.error(f"Попытка публикации #{attempt + 1} неудачна: {e}")
            if attempt == max_retries - 1:
                return False

    return False


async def _publish_post_attempt(post_data: Dict[str, Any]) -> bool:
    """Одна попытка публикации поста"""
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
            return await _publish_album(post_data, processed_text)
        elif post_data.get('original_message'):
            # Одиночное сообщение
            return await _publish_single_message(post_data, processed_text)
        else:
            # Только текст
            return await _publish_text_only(processed_text)

    except Exception as e:
        logger.error(f"Ошибка публикации поста #{post_data.get('id', 'unknown')}: {e}")
        return False


async def _publish_album(post_data: Dict[str, Any], processed_text: str) -> bool:
    """Публикует альбом"""
    try:
        from bot import bot
        messages = post_data['original_messages']
        logger.info(f"Публикуем альбом из {len(messages)} элементов")

        # Берем первое медиа для публикации с подписью
        first_message = messages[0]
        success = await _send_single_media(first_message, processed_text)

        # Если альбом из одного элемента, возвращаем результат
        if len(messages) == 1:
            return success

        # Если больше одного элемента, отправляем остальные без подписи
        for message in messages[1:]:
            try:
                await _send_single_media(message, "")
            except Exception as e:
                logger.error(f"Ошибка отправки элемента альбома: {e}")
                # Продолжаем отправку остальных

        logger.info(f"Альбом опубликован (пост #{post_data.get('id', 'unknown')})")
        return success

    except Exception as e:
        logger.error(f"Ошибка публикации альбома: {e}")
        return False


async def _publish_single_message(post_data: Dict[str, Any], processed_text: str) -> bool:
    """Публикует одиночное сообщение"""
    try:
        message = post_data['original_message']
        success = await _send_single_media(message, processed_text)
        if success:
            logger.info(f"Одиночное сообщение опубликовано (пост #{post_data.get('id', 'unknown')})")
        return success

    except Exception as e:
        logger.error(f"Ошибка публикации одиночного сообщения: {e}")
        return False


async def _publish_text_only(processed_text: str) -> bool:
    """Публикует только текст"""
    try:
        from bot import bot
        if processed_text.strip():
            await bot.send_message(
                chat_id=GROUP_ID,
                text=processed_text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logger.info("Текстовый пост опубликован")
            return True
        return False

    except Exception as e:
        logger.error(f"Ошибка публикации текста: {e}")
        return False


async def _send_single_media(message, caption: str) -> bool:
    """Отправляет одиночное медиа"""
    try:
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
                return True
            return False

        # Проверяем длину подписи
        if len(caption) > 1024:
            logger.warning(f"Подпись слишком длинная ({len(caption)} символов), обрезаем")
            caption = caption[:1020] + "..."

        success = False

        if media_info['type'] == 'photo':
            await bot.send_photo(
                chat_id=GROUP_ID,
                photo=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )
            success = True

        elif media_info['type'] == 'video':
            await bot.send_video(
                chat_id=GROUP_ID,
                video=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )
            success = True

        elif media_info['type'] == 'document':
            await bot.send_document(
                chat_id=GROUP_ID,
                document=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )
            success = True

        elif media_info['type'] == 'animation':
            await bot.send_animation(
                chat_id=GROUP_ID,
                animation=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )
            success = True

        elif media_info['type'] == 'voice':
            await bot.send_voice(
                chat_id=GROUP_ID,
                voice=media_info['file_id'],
                caption=caption,
                parse_mode="HTML"
            )
            success = True

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
            success = True

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
                success = True

        return success

    except Exception as e:
        logger.error(f"Ошибка отправки медиа типа {media_info.get('type', 'unknown')}: {e}")

        # Пытаемся отправить хотя бы текст при ошибке
        if caption.strip():
            try:
                from bot import bot
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=f"Ошибка отправки медиа. Текст поста:\n\n{caption}",
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                return True
            except Exception as text_error:
                logger.error(f"Не удалось отправить даже текст: {text_error}")

        return False


async def notify_admin_about_failure(post_data: Dict[str, Any], error_message: str):
    """Уведомляет админа о неудачной публикации"""
    try:
        from bot import bot
        from config import ADMIN_ID

        notification_text = (
            f"❌ **ОШИБКА ПУБЛИКАЦИИ**\n\n"
            f"Пост #{post_data.get('id', 'unknown')} не удалось опубликовать\n\n"
            f"Ошибка: {error_message}\n\n"
            f"Текст поста:\n{post_data.get('processed_text', '')[:200]}..."
        )

        await bot.send_message(
            chat_id=ADMIN_ID,
            text=notification_text,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка уведомления админа: {e}")