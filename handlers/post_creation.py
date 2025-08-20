# -*- coding: utf-8 -*-
import asyncio
import logging
from collections import defaultdict
from typing import Dict, List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from states import PostCreation, Menu
from keyboards import (
    PostAction, create_post_preview_keyboard, create_main_menu
)
from config import ADMIN_ID, MESSAGES, SETTINGS
from utils.post_storage import post_storage
from services.ai_processor import process_with_ai
from services.link_extractor import extract_links_from_entities, format_links_for_ai
from services.media_handler import MediaProcessor

router = Router()
logger = logging.getLogger(__name__)

# Хранилище для медиа-групп
albums: Dict[str, List[Message]] = defaultdict(list)
album_timers: Dict[str, asyncio.Task] = {}

media_processor = MediaProcessor()


async def show_post_preview(user_id: int, processed_text: str, original_messages: List[Message] = None,
                            original_message: Message = None):
    """Показывает превью поста пользователю"""
    # Добавляем пост в хранилище
    post_id = post_storage.add_pending_post(
        processed_text=processed_text,
        user_id=user_id,
        original_message=original_message,
        original_messages=original_messages
    )

    # Формируем текст превью
    preview_text = (
        f"{MESSAGES['preview_title'].format(post_id=post_id)}\n\n"
        f"{processed_text}\n\n"
        f"{MESSAGES['preview_footer']}"
    )

    # Ограничиваем длину
    if len(preview_text) > SETTINGS['max_preview_length']:
        preview_text = preview_text[:SETTINGS['max_preview_length'] - 50] + "...\n\n--- ТЕКСТ ОБРЕЗАН ---"

    keyboard = create_post_preview_keyboard(post_id)

    try:
        from bot import bot
        await bot.send_message(
            chat_id=user_id,
            text=preview_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logger.info(f"Отправлен превью поста #{post_id} пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки превью: {e}")


async def process_album_and_preview(media_group_id: str):
    """Обрабатывает альбом и показывает превью"""
    await asyncio.sleep(SETTINGS['album_processing_delay'])

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

        # Извлекаем ссылки
        links_data = extract_links_from_entities(original_text, caption_entities)
        formatted_links = format_links_for_ai(links_data)

        logger.info(f"Найденные ссылки в альбоме: {formatted_links}")

        # Обрабатываем через ИИ (промпт 1 - стиль и форматирование)
        processed_text = await process_with_ai(
            text=original_text,
            links=formatted_links,
            prompt_type='style_formatting'
        )

        # Проверяем лимит для медиа
        if len(processed_text) > SETTINGS['media_caption_limit']:
            logger.warning(f"Текст слишком длинный ({len(processed_text)} символов), обрезаем для медиа")
            processed_text = processed_text[:SETTINGS['media_caption_limit']] + "..."

        # Показываем превью
        await show_post_preview(ADMIN_ID, processed_text, original_messages=album_messages)

    except Exception as e:
        logger.error(f"Ошибка обработки альбома: {e}")


async def process_single_message_and_preview(message: Message):
    """Обрабатывает одиночное сообщение и показывает превью"""
    try:
        text = message.text or message.caption or ""
        entities = message.entities or message.caption_entities

        # Извлекаем ссылки
        links_data = extract_links_from_entities(text, entities)
        formatted_links = format_links_for_ai(links_data)

        logger.info(f"Обрабатываем одиночное сообщение: {text[:100]}...")
        logger.info(f"Найденные ссылки: {formatted_links}")

        # Обрабатываем через ИИ (промпт 1 - стиль и форматирование)
        processed_text = await process_with_ai(
            text=text,
            links=formatted_links,
            prompt_type='style_formatting'
        )

        # Показываем превью
        await show_post_preview(ADMIN_ID, processed_text, original_message=message)

        logger.info("Одиночное сообщение обработано, отправлен превью")

    except Exception as e:
        logger.error(f"Ошибка обработки одиночного сообщения: {e}")


# =============================================
# ОБРАБОТЧИКИ СООБЩЕНИЙ
# =============================================

@router.message(StateFilter(PostCreation.waiting), F.from_user.id == ADMIN_ID)
async def handle_post_creation_content(message: Message, state: FSMContext):
    """Обработка контента для создания поста"""

    # Проверяем, не ожидает ли пользователь редактирования поста
    editing_post_id = post_storage.get_user_editing_post(message.from_user.id)
    if editing_post_id:
        # Это доработка существующего поста
        await handle_post_improvement(message, editing_post_id)
        return

    # Это новый пост
    if message.media_group_id:
        # Часть альбома
        await handle_album_part(message)
    else:
        # Одиночное сообщение или медиа
        await process_single_message_and_preview(message)


@router.message(F.media_group_id & (F.from_user.id == ADMIN_ID))
async def handle_album_part(message: Message):
    """Обработка части альбома"""
    media_group_id = message.media_group_id
    albums[media_group_id].append(message)

    logger.info(f"Получена часть альбома {media_group_id} ({len(albums[media_group_id])}/...)")

    # Отменяем предыдущий таймер
    if media_group_id in album_timers:
        album_timers[media_group_id].cancel()

    # Устанавливаем новый таймер
    album_timers[media_group_id] = asyncio.create_task(
        process_album_and_preview(media_group_id)
    )


async def handle_post_improvement(message: Message, post_id: int):
    """Обработка доработки поста"""
    post_data = post_storage.get_pending_post(post_id)
    if not post_data:
        await message.reply("❌ Пост не найден")
        return

    try:
        original_text = post_data['processed_text']
        improvement_text = message.text

        combined_text = f"{original_text}\n\n{improvement_text}"

        # Обрабатываем через ИИ с промптом 3 (доработка)
        processed_text = await process_with_ai(
            text=combined_text,
            links="Дополнительная информация для интеграции",
            prompt_type='post_improvement'
        )

        # Обновляем пост
        post_storage.update_pending_post(
            post_id=post_id,
            processed_text=processed_text,
            awaiting_edit=False
        )

        # Показываем новый превью
        await show_post_preview(
            user_id=ADMIN_ID,
            processed_text=processed_text,
            original_messages=post_data.get('original_messages'),
            original_message=post_data.get('original_message')
        )

        logger.info(f"Пост #{post_id} доработан и показан новый превью")

    except Exception as e:
        logger.error(f"Ошибка доработки поста: {e}")
        await message.reply(f"❌ Ошибка доработки: {e}")


# =============================================
# CALLBACK ОБРАБОТЧИКИ
# =============================================

@router.callback_query(PostAction.filter())
async def handle_post_action(callback: CallbackQuery, callback_data: PostAction, state: FSMContext):
    """Обработчик действий с постом"""
    post_id = callback_data.post_id
    action = callback_data.action

    logger.info(f"Получено действие с постом: {action} для поста #{post_id}")

    post_data = post_storage.get_pending_post(post_id)
    if not post_data:
        await callback.answer("❌ Пост не найден", show_alert=True)
        logger.warning(f"Пост #{post_id} не найден в хранилище")
        return

    try:
        if action == "publish":
            # Публикация поста немедленно
            await handle_publish_now(callback, post_data, post_id)

        elif action == "schedule":
            # Переход к планированию
            await handle_schedule_request(callback, state, post_id)

        elif action == "edit":
            # Доработка поста
            await handle_edit_request(callback, post_id)

        elif action == "delete":
            # Удаление поста
            await handle_delete_post(callback, post_id)

        else:
            logger.warning(f"Неизвестное действие с постом: {action}")
            await callback.answer("❌ Неизвестное действие", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка обработки действия {action} для поста #{post_id}: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def handle_publish_now(callback: CallbackQuery, post_data: dict, post_id: int):
    """Обрабатывает немедленную публикацию поста"""
    try:
        from services.publisher import publish_post_now
        success = await publish_post_now(post_data)

        if success:
            post_storage.remove_pending_post(post_id)
            await callback.message.edit_text(
                text=MESSAGES['post_published'].format(post_id=post_id),
                reply_markup=None
            )
            await callback.answer("✅ Пост опубликован!")
            logger.info(f"Пост #{post_id} успешно опубликован")
        else:
            await callback.answer("❌ Ошибка публикации", show_alert=True)
            logger.error(f"Ошибка публикации поста #{post_id}")

    except Exception as e:
        logger.error(f"Ошибка при публикации поста #{post_id}: {e}")
        await callback.answer("❌ Ошибка публикации", show_alert=True)


async def handle_schedule_request(callback: CallbackQuery, state: FSMContext, post_id: int):
    """Обрабатывает запрос на планирование поста"""
    try:
        from handlers.scheduler import show_scheduler
        await show_scheduler(callback, state, post_id)
        logger.info(f"Переход к планированию поста #{post_id}")

    except Exception as e:
        logger.error(f"Ошибка перехода к планированию поста #{post_id}: {e}")
        await callback.answer("❌ Ошибка перехода к планированию", show_alert=True)


async def handle_edit_request(callback: CallbackQuery, post_id: int):
    """Обрабатывает запрос на редактирование поста"""
    try:
        post_storage.update_pending_post(post_id, awaiting_edit=True)
        await callback.message.edit_text(
            text=MESSAGES['edit_post_prompt'].format(post_id=post_id),
            reply_markup=None
        )
        await callback.answer("📝 Отправьте дополнения к посту")
        logger.info(f"Пост #{post_id} переведен в режим редактирования")

    except Exception as e:
        logger.error(f"Ошибка перевода поста #{post_id} в режим редактирования: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


async def handle_delete_post(callback: CallbackQuery, post_id: int):
    """Обрабатывает удаление поста"""
    try:
        post_storage.remove_pending_post(post_id)
        await callback.message.delete()
        await callback.answer(MESSAGES['post_deleted'])
        logger.info(f"Пост #{post_id} удален пользователем")

    except Exception as e:
        logger.error(f"Ошибка удаления поста #{post_id}: {e}")
        await callback.answer("❌ Ошибка удаления", show_alert=True)


# =============================================
# AUTO MODE (вне FSM)
# =============================================

@router.message(F.from_user.id == ADMIN_ID)
async def handle_auto_mode(message: Message, state: FSMContext):
    """Автоматический режим - обработка любых сообщений вне FSM"""
    current_state = await state.get_state()

    # Если уже в каком-то состоянии FSM, не обрабатываем
    if current_state is not None:
        logger.debug(f"Сообщение пропущено, пользователь в состоянии: {current_state}")
        return

    # Проверяем доработку поста
    editing_post_id = post_storage.get_user_editing_post(message.from_user.id)
    if editing_post_id:
        await handle_post_improvement(message, editing_post_id)
        return

    # Автоматическая обработка (режим AUTO)
    logger.info(f"AUTO режим: получено сообщение от пользователя {message.from_user.id}")

    if message.media_group_id:
        await handle_album_part(message)
    else:
        # Для AUTO режима используем промпт 2 (обработка для группы)
        await process_single_for_auto_mode(message)


async def process_single_for_auto_mode(message: Message):
    """Обрабатывает одиночное сообщение в AUTO режиме"""
    try:
        text = message.text or message.caption or ""
        entities = message.entities or message.caption_entities

        # Извлекаем ссылки
        links_data = extract_links_from_entities(text, entities)
        formatted_links = format_links_for_ai(links_data)

        logger.info(f"AUTO режим: обрабатываем сообщение: {text[:100]}...")

        # Обрабатываем через ИИ (промпт 2 - обработка для группы)
        processed_text = await process_with_ai(
            text=text,
            links=formatted_links,
            prompt_type='group_processing'
        )

        # Показываем превью
        await show_post_preview(ADMIN_ID, processed_text, original_message=message)

        logger.info("AUTO режим: сообщение обработано, отправлен превью")

    except Exception as e:
        logger.error(f"Ошибка AUTO режима: {e}")


# Обработка медиа вне FSM для AUTO режима
@router.message(
    F.content_type.in_({
        ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT,
        ContentType.ANIMATION, ContentType.VOICE, ContentType.VIDEO_NOTE
    }) & (F.from_user.id == ADMIN_ID)
)
async def handle_auto_mode_media(message: Message, state: FSMContext):
    """Обработка медиа в AUTO режиме"""
    current_state = await state.get_state()

    # Если в FSM состоянии, пропускаем
    if current_state is not None:
        logger.debug(f"Медиа пропущено, пользователь в состоянии: {current_state}")
        return

    if message.media_group_id:
        return  # Обработается в handle_album_part

    logger.info(f"AUTO режим: получено медиа от пользователя {message.from_user.id}")
    await process_single_for_auto_mode(message)


# Обработка неизвестных callback'ов для постов
@router.callback_query(StateFilter(PostCreation))
async def handle_unknown_post_callback(callback: CallbackQuery):
    """Обработка неизвестных callback'ов в создании постов"""
    logger.warning(f"Неизвестный callback в создании поста: {callback.data}")
    await callback.answer("❌ Неизвестное действие", show_alert=True)