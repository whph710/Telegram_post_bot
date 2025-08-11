# -*- coding: utf-8 -*-
import logging
import asyncio
from collections import defaultdict
from typing import Dict, List

from aiogram import types, F, Router
from aiogram.enums import ContentType

from bot import bot
from config import GROUP_ID, MY_ID
from link_extractor import extract_links_from_entities, format_links_for_ai
from ai_processor import process_with_deepseek
from media_handler import MediaProcessor

router = Router()
logger = logging.getLogger(__name__)

# Хранилище для медиа-групп
albums: Dict[str, List[types.Message]] = defaultdict(list)
album_timers: Dict[str, asyncio.Task] = {}

media_processor = MediaProcessor()


async def process_and_send_album(media_group_id: str):
    """Обрабатывает и отправляет альбом с AI обработкой"""
    await asyncio.sleep(2)  # Ждем завершения получения всех медиа

    if media_group_id not in albums:
        return

    album_messages = albums.pop(media_group_id)
    album_timers.pop(media_group_id, None)

    if not album_messages:
        return

    try:
        # Берем caption и entities из первого сообщения
        first_message = album_messages[0]
        original_text = first_message.caption or ""
        caption_entities = first_message.caption_entities

        logger.info(f"Обрабатываем альбом с текстом: {original_text[:100]}...")

        # Извлекаем ссылки
        links_data = extract_links_from_entities(original_text, caption_entities)
        formatted_links = format_links_for_ai(links_data)

        logger.info(f"Найденные ссылки в альбоме: {formatted_links}")

        # Обрабатываем через AI
        processed_text = await process_with_deepseek(original_text, formatted_links)

        # Проверяем длину обработанного текста
        if len(processed_text) > 1024:
            logger.warning(f"Текст слишком длинный ({len(processed_text)} символов), обрезаем")
            processed_text = processed_text[:1020] + "..."

        # Строим медиа-группу с обработанным текстом
        media_group = media_processor.build_media_group(album_messages, processed_text)

        # Отправляем в группу
        await bot.send_media_group(chat_id=GROUP_ID, media=media_group.build())

        logger.info(f"Альбом отправлен ({len(album_messages)} элементов) с обработанным текстом")

    except Exception as e:
        logger.error(f"О шибка обработки альбома: {e}")

        # Пытаемся отправить без AI обработки
        try:
            first_message = album_messages[0]
            fallback_text = first_message.caption or ""

            if len(fallback_text) > 1024:
                fallback_text = fallback_text[:1020] + "..."

            media_group = media_processor.build_media_group(album_messages, fallback_text)
            await bot.send_media_group(chat_id=GROUP_ID, media=media_group.build())

            logger.info("Альбом отправлен с оригинальным текстом (fallback)")

        except Exception as fallback_error:
            logger.error(f"❌ Критическая ошибка отправки альбома: {fallback_error}")


async def process_and_send_single(message: types.Message):
    """Обрабатывает и отправляет одиночное сообщение"""
    try:
        # Извлекаем текст и ссылки
        text = message.text or message.caption or ""
        entities = message.entities or message.caption_entities

        links_data = extract_links_from_entities(text, entities)
        formatted_links = format_links_for_ai(links_data)

        logger.info(f"Обрабатываем одиночное сообщение: {text[:100]}...")
        logger.info(f"Найденные ссылки: {formatted_links}")

        # Обрабатываем через AI
        processed_text = await process_with_deepseek(text, formatted_links)

        # Определяем тип медиа и отправляем
        media_info = media_processor.extract_media_info(message)

        if media_info['has_media']:
            # Отправляем с медиа (одиночное медиа как медиагруппа для единообразия)
            if media_info['type'] in ['photo', 'video', 'document']:
                # Проверяем длину текста для медиа-группы
                if len(processed_text) > 1024:
                    logger.warning(f"⚠️ Текст слишком длинный ({len(processed_text)} символов), обрезаем")
                    processed_text = processed_text[:1020] + "..."

                media_group = media_processor.build_single_media_group(message, processed_text)
                await bot.send_media_group(chat_id=GROUP_ID, media=media_group.build())
            else:
                # Для других типов медиа (animation, voice, video_note) отправляем как есть
                if media_info['type'] == 'animation':
                    await bot.send_animation(
                        chat_id=GROUP_ID,
                        animation=media_info['file_id'],
                        caption=processed_text,
                        parse_mode="HTML"
                    )
                elif media_info['type'] == 'voice':
                    await bot.send_voice(
                        chat_id=GROUP_ID,
                        voice=media_info['file_id'],
                        caption=processed_text,
                        parse_mode="HTML"
                    )
                elif media_info['type'] == 'video_note':
                    # Video note не поддерживает caption, отправляем отдельно
                    await bot.send_video_note(chat_id=GROUP_ID, video_note=media_info['file_id'])
                    if processed_text.strip():
                        await bot.send_message(
                            chat_id=GROUP_ID,
                            text=processed_text,
                            parse_mode="HTML"
                        )
        else:
            # Только текст
            if processed_text.strip():
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=processed_text,
                    parse_mode="HTML"
                )

        logger.info(f"✅ Одиночное сообщение обработано и отправлено")

    except Exception as e:
        logger.error(f"❌ Ошибка обработки одиночного сообщения: {e}")

        # Пытаемся отправить оригинальное сообщение
        try:
            original_text = message.text or message.caption or ""
            if original_text.strip():
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=original_text,
                    parse_mode=None  # Без HTML парсинга для безопасности
                )
                logger.info("📤 Отправлено оригинальное сообщение (fallback)")
        except Exception as fallback_error:
            logger.error(f"❌ Критическая ошибка отправки: {fallback_error}")


@router.message(F.media_group_id & (F.from_user.id == MY_ID))
async def handle_album_part(message: types.Message):
    """Обработка части альбома"""
    media_group_id = message.media_group_id
    albums[media_group_id].append(message)

    logger.info(f"📸 Получена часть альбома {media_group_id} ({len(albums[media_group_id])}/...)")

    # Обновляем таймер
    if media_group_id in album_timers:
        album_timers[media_group_id].cancel()

    album_timers[media_group_id] = asyncio.create_task(
        process_and_send_album(media_group_id)
    )


@router.message(
    (F.content_type.in_({
        ContentType.TEXT,
        ContentType.PHOTO,
        ContentType.VIDEO,
        ContentType.DOCUMENT,
        ContentType.ANIMATION,
        ContentType.VOICE,
        ContentType.VIDEO_NOTE
    })) & (F.from_user.id == MY_ID)
)
async def handle_single_message(message: types.Message):
    """Обработка одиночных сообщений"""
    if message.media_group_id:
        return  # Обрабатывается как альбом

    logger.info(f"📨 Получено одиночное сообщение от пользователя {message.from_user.id}")
    await process_and_send_single(message)