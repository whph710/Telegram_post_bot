# -*- coding: utf-8 -*-
import logging
import asyncio
from collections import defaultdict
from typing import Dict, List

from aiogram import types, F, Router
from aiogram.enums import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

from bot import bot
from config import GROUP_ID, MY_ID
from link_extractor import extract_links_from_entities, format_links_for_ai
from ai_processor import process_with_deepseek
from media_handler import MediaProcessor

router = Router()
logger = logging.getLogger(__name__)

# Хранилище для медиа-групп и состояний
albums: Dict[str, List[types.Message]] = defaultdict(list)
album_timers: Dict[str, asyncio.Task] = {}
pending_posts: Dict[int, Dict] = {}  # Хранилище ожидающих постов

media_processor = MediaProcessor()


class PostAction(CallbackData, prefix="post"):
    action: str
    post_id: int


def create_preview_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для предпросмотра поста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Запостить",
                callback_data=PostAction(action="publish", post_id=post_id).pack()
            ),
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=PostAction(action="cancel", post_id=post_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Доработать",
                callback_data=PostAction(action="edit", post_id=post_id).pack()
            ),
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=PostAction(action="delete", post_id=post_id).pack()
            )
        ]
    ])


async def show_preview(user_id: int, processed_text: str, original_messages: List[types.Message] = None,
                       original_message: types.Message = None):
    """Показывает предпросмотр поста пользователю"""
    post_id = len(pending_posts) + 1

    # Сохраняем данные поста
    pending_posts[post_id] = {
        'processed_text': processed_text,
        'original_messages': original_messages,
        'original_message': original_message,
        'user_id': user_id,
        'awaiting_edit': False
    }

    preview_text = f"ПРЕДПРОСМОТР ПОСТА #{post_id}\n\n{processed_text}\n\n--- КОНЕЦ ПОСТА ---"

    # Ограничиваем длину предпросмотра
    if len(preview_text) > 4000:
        preview_text = preview_text[:3950] + "...\n\n--- ТЕКСТ ОБРЕЗАН ---"

    keyboard = create_preview_keyboard(post_id)

    try:
        await bot.send_message(
            chat_id=user_id,
            text=preview_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True  # ДОБАВЛЕНО: отключаем превью
        )
        logger.info(f"Отправлен предпросмотр поста #{post_id} пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки предпросмотра: {e}")


async def process_and_send_album(media_group_id: str):
    """Обрабатывает альбом и показывает предпросмотр"""
    await asyncio.sleep(2)

    if media_group_id not in albums:
        return

    album_messages = albums.pop(media_group_id)
    album_timers.pop(media_group_id, None)

    if not album_messages:
        return

    try:
        first_message = album_messages[0]
        original_text = first_message.caption or ""
        caption_entities = first_message.caption_entities

        logger.info(f"Обрабатываем альбом с текстом: {original_text[:100]}...")

        links_data = extract_links_from_entities(original_text, caption_entities)
        formatted_links = format_links_for_ai(links_data)

        logger.info(f"Найденные ссылки в альбоме: {formatted_links}")

        processed_text = await process_with_deepseek(original_text, formatted_links)

        if len(processed_text) > 1024:
            logger.warning(f"Текст слишком длинный ({len(processed_text)} символов), обрезаем для медиа")
            processed_text = processed_text[:1020] + "..."

        # Показываем предпросмотр вместо прямой отправки
        await show_preview(MY_ID, processed_text, original_messages=album_messages)

    except Exception as e:
        logger.error(f"Ошибка обработки альбома: {e}")


async def process_and_send_single(message: types.Message):
    """Обрабатывает одиночное сообщение и показывает предпросмотр"""
    try:
        text = message.text or message.caption or ""
        entities = message.entities or message.caption_entities

        links_data = extract_links_from_entities(text, entities)
        formatted_links = format_links_for_ai(links_data)

        logger.info(f"Обрабатываем одиночное сообщение: {text[:100]}...")
        logger.info(f"Найденные ссылки: {formatted_links}")

        processed_text = await process_with_deepseek(text, formatted_links)

        # Показываем предпросмотр вместо прямой отправки
        await show_preview(MY_ID, processed_text, original_message=message)

        logger.info(f"Одиночное сообщение обработано, отправлен предпросмотр")

    except Exception as e:
        logger.error(f"Ошибка обработки одиночного сообщения: {e}")


async def publish_post(post_id: int):
    """Публикует пост в группу"""
    if post_id not in pending_posts:
        return False

    post_data = pending_posts[post_id]
    processed_text = post_data['processed_text']

    try:
        if post_data['original_messages']:
            # Альбом
            messages = post_data['original_messages']
            media_group = media_processor.build_media_group(messages, processed_text)
            await bot.send_media_group(
                chat_id=GROUP_ID,
                media=media_group.build()
            )
            logger.info(f"Альбом опубликован (пост #{post_id})")

        elif post_data['original_message']:
            # Одиночное сообщение
            message = post_data['original_message']
            media_info = media_processor.extract_media_info(message)

            if media_info['has_media']:
                if media_info['type'] in ['photo', 'video', 'document']:
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
                        disable_web_page_preview=True  # ДОБАВЛЕНО: отключаем превью
                    )
                elif media_info['type'] == 'voice':
                    await bot.send_voice(
                        chat_id=GROUP_ID,
                        voice=media_info['file_id'],
                        caption=processed_text,
                        parse_mode="HTML",
                        disable_web_page_preview=True  # ДОБАВЛЕНО: отключаем превью
                    )
                elif media_info['type'] == 'video_note':
                    await bot.send_video_note(
                        chat_id=GROUP_ID,
                        video_note=media_info['file_id']
                    )
                    if processed_text.strip():
                        await bot.send_message(
                            chat_id=GROUP_ID,
                            text=processed_text,
                            parse_mode="HTML",
                            disable_web_page_preview=True  # ДОБАВЛЕНО: отключаем превью
                        )
            else:
                # Только текст
                if processed_text.strip():
                    await bot.send_message(
                        chat_id=GROUP_ID,
                        text=processed_text,
                        parse_mode="HTML",
                        disable_web_page_preview=True  # ДОБАВЛЕНО: отключаем превью
                    )

            logger.info(f"Одиночное сообщение опубликовано (пост #{post_id})")

        # Удаляем из ожидающих
        del pending_posts[post_id]
        return True

    except Exception as e:
        logger.error(f"Ошибка публикации поста #{post_id}: {e}")
        return False


@router.callback_query(PostAction.filter())
async def handle_post_action(callback: types.CallbackQuery, callback_data: PostAction):
    """Обработчик действий с постом"""
    post_id = callback_data.post_id
    action = callback_data.action

    if post_id not in pending_posts:
        await callback.answer("Пост не найден", show_alert=True)
        return

    post_data = pending_posts[post_id]

    if action == "publish":
        success = await publish_post(post_id)
        if success:
            await callback.message.edit_text(
                f"Пост #{post_id} успешно опубликован!",
                reply_markup=None
            )
            await callback.answer("Пост опубликован!")
        else:
            await callback.answer("Ошибка публикации", show_alert=True)

    elif action == "cancel":
        del pending_posts[post_id]
        await callback.message.edit_text(
            f"Пост #{post_id} отменен",
            reply_markup=None
        )
        await callback.answer("Пост отменен")

    elif action == "edit":
        post_data['awaiting_edit'] = True
        await callback.message.edit_text(
            f"Пост #{post_id} ожидает доработки.\n\nОтправьте сообщение с дополнениями:",
            reply_markup=None
        )
        await callback.answer("Отправьте дополнения к посту")

    elif action == "delete":
        del pending_posts[post_id]
        await callback.message.delete()
        await callback.answer("Пост удален")


@router.message(F.text & (F.from_user.id == MY_ID))
async def handle_edit_message(message: types.Message):
    """Обработчик сообщений для доработки постов"""
    # Проверяем, есть ли посты, ожидающие доработки
    awaiting_post = None
    for post_id, post_data in pending_posts.items():
        if post_data.get('awaiting_edit', False) and post_data['user_id'] == message.from_user.id:
            awaiting_post = post_id
            break

    if awaiting_post:
        # Это доработка существующего поста
        post_data = pending_posts[awaiting_post]
        original_text = post_data['processed_text']
        edit_text = message.text

        combined_text = f"{original_text}\n\n{edit_text}"

        # Обрабатываем через AI с prompt2.txt
        try:
            processed_text = await process_with_deepseek(
                combined_text,
                "Ссылки и упоминания не найдены",
                prompt_file='prompt2.txt'
            )

            # Обновляем данные поста
            post_data['processed_text'] = processed_text
            post_data['awaiting_edit'] = False

            # Показываем новый предпросмотр
            await show_preview(MY_ID, processed_text,
                               original_messages=post_data.get('original_messages'),
                               original_message=post_data.get('original_message'))

            logger.info(f"Пост #{awaiting_post} доработан и показан новый предпросмотр")

        except Exception as e:
            logger.error(f"Ошибка доработки поста: {e}")
            await message.reply(f"Ошибка обработки доработки: {e}")
    else:
        # Это новое сообщение для обработки
        await process_and_send_single(message)


@router.message(F.media_group_id & (F.from_user.id == MY_ID))
async def handle_album_part(message: types.Message):
    """Обработка части альбома"""
    media_group_id = message.media_group_id
    albums[media_group_id].append(message)

    logger.info(f"Получена часть альбома {media_group_id} ({len(albums[media_group_id])}/...)")

    if media_group_id in album_timers:
        album_timers[media_group_id].cancel()

    album_timers[media_group_id] = asyncio.create_task(
        process_and_send_album(media_group_id)
    )


@router.message(
    (F.content_type.in_({
        ContentType.PHOTO,
        ContentType.VIDEO,
        ContentType.DOCUMENT,
        ContentType.ANIMATION,
        ContentType.VOICE,
        ContentType.VIDEO_NOTE
    })) & (F.from_user.id == MY_ID)
)
async def handle_single_media(message: types.Message):
    """Обработка одиночных медиа сообщений"""
    if message.media_group_id:
        return  # Обрабатывается как альбом

    logger.info(f"Получено одиночное медиа сообщение от пользователя {message.from_user.id}")
    await process_and_send_single(message)