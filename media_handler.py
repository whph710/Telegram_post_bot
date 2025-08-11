# -*- coding: utf-8 -*-
from typing import List, Optional, Dict, Any
from aiogram import types
from aiogram.utils.media_group import MediaGroupBuilder
import logging

logger = logging.getLogger(__name__)


class MediaProcessor:
    def __init__(self):
        self.supported_types = {
            'photo', 'video', 'document', 'animation', 'voice', 'video_note'
        }

    def extract_media_info(self, message: types.Message) -> Dict[str, Any]:
        """Извлекает информацию о медиа из сообщения"""
        media_info = {
            'type': None,
            'file_id': None,
            'caption': message.caption or "",
            'caption_entities': message.caption_entities,
            'has_media': False
        }

        # Определяем тип медиа
        if message.photo:
            media_info.update({
                'type': 'photo',
                'file_id': message.photo[-1].file_id,
                'has_media': True
            })
        elif message.video:
            media_info.update({
                'type': 'video',
                'file_id': message.video.file_id,
                'has_media': True
            })
        elif message.document:
            media_info.update({
                'type': 'document',
                'file_id': message.document.file_id,
                'has_media': True
            })
        elif message.animation:
            media_info.update({
                'type': 'animation',
                'file_id': message.animation.file_id,
                'has_media': True
            })
        elif message.voice:
            media_info.update({
                'type': 'voice',
                'file_id': message.voice.file_id,
                'has_media': True
            })
        elif message.video_note:
            media_info.update({
                'type': 'video_note',
                'file_id': message.video_note.file_id,
                'has_media': True
            })

        return media_info

    def build_media_group(self, messages: List[types.Message], processed_caption: str) -> MediaGroupBuilder:
        """Строит медиа-группу для отправки (для альбомов)"""
        media_group = MediaGroupBuilder()

        for idx, msg in enumerate(messages):
            media_info = self.extract_media_info(msg)
            caption = processed_caption if idx == 0 else None

            try:
                if media_info['type'] == 'photo':
                    media_group.add_photo(
                        media=media_info['file_id'],
                        caption=caption,
                        parse_mode="HTML"
                    )
                elif media_info['type'] == 'video':
                    media_group.add_video(
                        media=media_info['file_id'],
                        caption=caption,
                        parse_mode="HTML"
                    )
                elif media_info['type'] == 'document':
                    media_group.add_document(
                        media=media_info['file_id'],
                        caption=caption,
                        parse_mode="HTML"
                    )
                else:
                    logger.warning(f"Неподдерживаемый тип медиа в альбоме: {media_info['type']}")
            except Exception as e:
                logger.error(f"Ошибка добавления медиа в группу: {e}")

        return media_group

    def build_single_media_group(self, message: types.Message, processed_caption: str) -> MediaGroupBuilder:
        """Строит медиа-группу для одиночного медиа (для единообразия отправки)"""
        media_group = MediaGroupBuilder()
        media_info = self.extract_media_info(message)

        try:
            if media_info['type'] == 'photo':
                media_group.add_photo(
                    media=media_info['file_id'],
                    caption=processed_caption,
                    parse_mode="HTML"
                )
            elif media_info['type'] == 'video':
                media_group.add_video(
                    media=media_info['file_id'],
                    caption=processed_caption,
                    parse_mode="HTML"
                )
            elif media_info['type'] == 'document':
                media_group.add_document(
                    media=media_info['file_id'],
                    caption=processed_caption,
                    parse_mode="HTML"
                )
            else:
                logger.warning(f"Попытка создать медиагруппу для неподдерживаемого типа: {media_info['type']}")
        except Exception as e:
            logger.error(f"Ошибка создания одиночной медиагруппы: {e}")

        return media_group