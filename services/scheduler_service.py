# -*- coding: utf-8 -*-
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from utils.post_storage import post_storage
from utils.time_slots import time_slot_manager
from config import GROUP_ID

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис для планирования и автоматической публикации постов"""

    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Запускает планировщик"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Планировщик постов запущен")

    async def stop(self):
        """Останавливает планировщик"""
        if not self.is_running:
            return

        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Планировщик постов остановлен")

    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        try:
            while self.is_running:
                try:
                    await self._check_and_publish_posts()
                    await asyncio.sleep(60)  # Проверяем каждую минуту
                except Exception as e:
                    logger.error(f"Ошибка в цикле планировщика: {e}")
                    await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Цикл планировщика отменен")

    async def _check_and_publish_posts(self):
        """Проверяет и публикует готовые посты"""
        try:
            pending_posts = post_storage.get_pending_scheduled_posts()
        except Exception as e:
            logger.error(f"Ошибка получения постов для публикации: {e}")
            return

        if not pending_posts:
            return

        logger.info(f"Найдено {len(pending_posts)} постов для публикации")

        for post_data in pending_posts:
            try:
                success = await self._publish_scheduled_post(post_data)
                if success:
                    post_storage.mark_post_published(post_data['id'])
                    logger.info(f"Пост #{post_data['id']} успешно опубликован по расписанию")
                else:
                    logger.error(f"Ошибка публикации поста #{post_data['id']}")
            except Exception as e:
                logger.error(f"Ошибка публикации поста #{post_data['id']}: {e}")

    async def _publish_scheduled_post(self, post_data: dict) -> bool:
        """Публикует запланированный пост"""
        try:
            # Используем существующую логику из publisher
            from services.publisher import publish_post_now
            return await publish_post_now(post_data)

        except Exception as e:
            logger.error(f"Ошибка публикации поста: {e}")
            return False

    def schedule_post(
            self,
            processed_text: str,
            publish_time: datetime,
            user_id: int,
            original_message=None,
            original_messages=None
    ) -> int:
        """Планирует пост на определенное время"""
        post_id = post_storage.schedule_post(
            processed_text=processed_text,
            publish_time=publish_time,
            user_id=user_id,
            original_message=original_message,
            original_messages=original_messages
        )

        logger.info(f"Запланирован пост #{post_id} на {publish_time}")
        return post_id

    def get_quick_schedule_time(self, option: str) -> Optional[datetime]:
        """Получает время для быстрых опций планирования"""
        now = datetime.now()
        return time_slot_manager.get_quick_schedule_time(option, now)

    def parse_custom_time(self, time_str: str) -> Optional[datetime]:
        """Парсит пользовательское время"""
        parsed_time = time_slot_manager.parse_user_datetime(time_str)

        if parsed_time and time_slot_manager.is_time_in_slots(parsed_time):
            return parsed_time
        elif parsed_time:
            # Время не в слотах, находим ближайший доступный
            return time_slot_manager.get_next_available_slot(parsed_time)

        return None

    def distribute_posts_in_schedule(self, count: int, days_ahead: int = 7) -> List[datetime]:
        """Распределяет посты по расписанию"""
        start_time = datetime.now() + timedelta(minutes=30)  # Начинаем через 30 минут
        return time_slot_manager.distribute_posts_in_slots(count, start_time, days_ahead)

    def get_schedule_summary(self) -> str:
        """Возвращает описание расписания"""
        return time_slot_manager.get_schedule_summary()

    def format_time_for_user(self, dt: datetime) -> str:
        """Форматирует время для пользователя"""
        return time_slot_manager.format_datetime_for_user(dt)


# Глобальный экземпляр планировщика (будет инициализирован в main.py)
scheduler_service: Optional[SchedulerService] = None