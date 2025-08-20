# -*- coding: utf-8 -*-
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PostStorage:
    """Хранилище для постов в памяти (без БД)"""

    def __init__(self):
        # Ожидающие действий посты (превью)
        self.pending_posts: Dict[int, Dict[str, Any]] = {}

        # Запланированные посты
        self.scheduled_posts: Dict[int, Dict[str, Any]] = {}

        # Счетчики ID
        self._pending_counter = 0
        self._scheduled_counter = 0

    # =============================================
    # ОЖИДАЮЩИЕ ПОСТЫ (ПРЕВЬЮ)
    # =============================================

    def add_pending_post(
            self,
            processed_text: str,
            user_id: int,
            original_message=None,
            original_messages=None
    ) -> int:
        """Добавляет пост в ожидающие (для превью)"""
        self._pending_counter += 1
        post_id = self._pending_counter

        self.pending_posts[post_id] = {
            'id': post_id,
            'processed_text': processed_text,
            'user_id': user_id,
            'original_message': original_message,
            'original_messages': original_messages,
            'awaiting_edit': False,
            'created_at': datetime.now()
        }

        logger.info(f"Добавлен ожидающий пост #{post_id} от пользователя {user_id}")
        return post_id

    def get_pending_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Получает ожидающий пост по ID"""
        return self.pending_posts.get(post_id)

    def update_pending_post(self, post_id: int, **kwargs) -> bool:
        """Обновляет данные ожидающего поста"""
        if post_id in self.pending_posts:
            self.pending_posts[post_id].update(kwargs)
            return True
        return False

    def remove_pending_post(self, post_id: int) -> bool:
        """Удаляет ожидающий пост"""
        if post_id in self.pending_posts:
            del self.pending_posts[post_id]
            logger.info(f"Удален ожидающий пост #{post_id}")
            return True
        return False

    def get_user_editing_post(self, user_id: int) -> Optional[int]:
        """Находит пост пользователя, ожидающий редактирования"""
        for post_id, post_data in self.pending_posts.items():
            if (post_data['user_id'] == user_id and
                    post_data.get('awaiting_edit', False)):
                return post_id
        return None

    # =============================================
    # ЗАПЛАНИРОВАННЫЕ ПОСТЫ
    # =============================================

    def schedule_post(
            self,
            processed_text: str,
            publish_time: datetime,
            user_id: int,
            original_message=None,
            original_messages=None
    ) -> int:
        """Добавляет пост в расписание"""
        self._scheduled_counter += 1
        post_id = self._scheduled_counter

        self.scheduled_posts[post_id] = {
            'id': post_id,
            'processed_text': processed_text,
            'publish_time': publish_time,
            'user_id': user_id,
            'original_message': original_message,
            'original_messages': original_messages,
            'created_at': datetime.now(),
            'status': 'scheduled'  # scheduled, published, cancelled
        }

        logger.info(f"Запланирован пост #{post_id} на {publish_time}")
        return post_id

    def get_scheduled_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Получает запланированный пост по ID"""
        return self.scheduled_posts.get(post_id)

    def get_scheduled_posts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получает список запланированных постов"""
        posts = [
            post for post in self.scheduled_posts.values()
            if post['status'] == 'scheduled'
        ]

        # Сортируем по времени публикации
        posts.sort(key=lambda x: x['publish_time'])

        if limit:
            posts = posts[:limit]

        return posts

    def get_pending_scheduled_posts(self) -> List[Dict[str, Any]]:
        """Получает посты, готовые к публикации (время пришло)"""
        now = datetime.now()
        pending = []

        for post in self.scheduled_posts.values():
            if (post['status'] == 'scheduled' and
                    post['publish_time'] <= now):
                pending.append(post)

        return pending

    def update_scheduled_post(self, post_id: int, **kwargs) -> bool:
        """Обновляет данные запланированного поста"""
        if post_id in self.scheduled_posts:
            self.scheduled_posts[post_id].update(kwargs)
            return True
        return False

    def cancel_scheduled_post(self, post_id: int) -> bool:
        """Отменяет запланированный пост"""
        if post_id in self.scheduled_posts:
            self.scheduled_posts[post_id]['status'] = 'cancelled'
            logger.info(f"Отменен запланированный пост #{post_id}")
            return True
        return False

    def mark_post_published(self, post_id: int) -> bool:
        """Отмечает пост как опубликованный"""
        if post_id in self.scheduled_posts:
            self.scheduled_posts[post_id]['status'] = 'published'
            logger.info(f"Пост #{post_id} отмечен как опубликованный")
            return True
        return False

    def remove_scheduled_post(self, post_id: int) -> bool:
        """Удаляет запланированный пост"""
        if post_id in self.scheduled_posts:
            del self.scheduled_posts[post_id]
            logger.info(f"Удален запланированный пост #{post_id}")
            return True
        return False

    # =============================================
    # СТАТИСТИКА И УТИЛИТЫ
    # =============================================

    def get_stats(self) -> Dict[str, int]:
        """Получает статистику постов"""
        scheduled_count = len([
            p for p in self.scheduled_posts.values()
            if p['status'] == 'scheduled'
        ])

        published_count = len([
            p for p in self.scheduled_posts.values()
            if p['status'] == 'published'
        ])

        return {
            'pending_posts': len(self.pending_posts),
            'scheduled_posts': scheduled_count,
            'published_posts': published_count,
            'total_processed': len(self.pending_posts) + len(self.scheduled_posts)
        }

    def cleanup_old_posts(self, days: int = 7):
        """Очищает старые посты (опубликованные и отмененные)"""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

        # Очищаем старые ожидающие посты
        to_remove_pending = [
            post_id for post_id, post_data in self.pending_posts.items()
            if post_data['created_at'] < cutoff_date
        ]

        for post_id in to_remove_pending:
            del self.pending_posts[post_id]

        # Очищаем старые опубликованные/отмененные посты
        to_remove_scheduled = [
            post_id for post_id, post_data in self.scheduled_posts.items()
            if (post_data['status'] in ['published', 'cancelled'] and
                post_data['created_at'] < cutoff_date)
        ]

        for post_id in to_remove_scheduled:
            del self.scheduled_posts[post_id]

        if to_remove_pending or to_remove_scheduled:
            logger.info(
                f"Очищено {len(to_remove_pending)} ожидающих и "
                f"{len(to_remove_scheduled)} запланированных постов старше {days} дней"
            )


# Глобальный экземпляр хранилища
post_storage = PostStorage()