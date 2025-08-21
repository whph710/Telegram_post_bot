# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from states import PostCreation, Menu
from keyboards import (
    ScheduleAction, QueueAction,
    create_simple_scheduler_keyboard, create_back_to_menu_keyboard,
    create_queue_item_keyboard
)
from config import ADMIN_ID, MESSAGES, POSTING_SCHEDULE
from utils.post_storage import post_storage
from utils.time_slots import time_slot_manager

router = Router()
logger = logging.getLogger(__name__)


# =============================================
# ОБРАБОТЧИКИ ПЛАНИРОВЩИКА
# =============================================

@router.callback_query(ScheduleAction.filter())
async def handle_schedule_action(callback: CallbackQuery, callback_data: ScheduleAction, state: FSMContext):
    """Обработчик действий планировщика"""
    action = callback_data.action
    post_id = callback_data.post_id
    day = callback_data.day
    time_slot = callback_data.time_slot

    logger.info(f"Планировщик: {action}, post_id: {post_id}, day: {day}, time_slot: {time_slot}")

    # Получаем пост
    post_data = post_storage.get_pending_post(post_id)
    if not post_data:
        await callback.answer("❌ Пост не найден", show_alert=True)
        logger.warning(f"Пост #{post_id} не найден при планировании")
        return

    try:
        if action == "none":
            # Планируем пост
        scheduled_id = post_storage.schedule_post(
            processed_text=post_data['processed_text'],
            publish_time=schedule_time,
            user_id=post_data['user_id'],
            original_message=post_data.get('original_message'),
            original_messages=post_data.get('original_messages')
        )

        # Удаляем из ожидающих
        post_storage.remove_pending_post(post_id)

        # Форматируем время для пользователя
        formatted_time = time_slot_manager.format_datetime_for_user(schedule_time)

        await callback.message.edit_text(
            text=f"✅ **ПОСТ ЗАПЛАНИРОВАН**\n\n"
                 f"📅 Время публикации: **{formatted_time}**\n\n"
                 f"Пост будет автоматически опубликован в указанное время.",
            reply_markup=create_back_to_menu_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer(f"✅ Запланировано на {formatted_time}")

        # Возвращаем в главное меню
        await state.set_state(Menu.main)
        logger.info(f"Пост #{post_id} запланирован на {schedule_time}")

    except Exception as e:
        logger.error(f"Ошибка завершения планирования: {e}")
        await callback.answer("❌ Ошибка планирования", show_alert=True)


# =============================================
# ОБРАБОТЧИКИ ОЧЕРЕДИ
# =============================================

@router.callback_query(QueueAction.filter())
async def handle_queue_action(callback: CallbackQuery, callback_data: QueueAction, state: FSMContext):
    """Обработчик действий с очередью"""
    action = callback_data.action
    post_id = callback_data.post_id

    logger.info(f"Получено действие с очередью: {action}, post_id: {post_id}")

    try:
        if action == "refresh":
            # Обновление списка очереди
            from handlers.menu import show_queue
            await show_queue(callback, state)

        elif action == "publish_now" and post_id:
            # Публикация поста немедленно из очереди
            await handle_queue_publish_now(callback, post_id, state)

        elif action == "change_time" and post_id:
            # Изменение времени поста - показываем планировщик
            await handle_queue_change_time(callback, post_id, state)

        elif action == "cancel" and post_id:
            # Отмена публикации
            await handle_queue_cancel(callback, post_id, state)

        else:
            logger.warning(f"Неизвестное действие с очередью: {action}")
            await callback.answer("❌ Неизвестное действие", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка обработки действия с очередью {action}: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def handle_queue_publish_now(callback: CallbackQuery, post_id: int, state: FSMContext):
    """Публикует пост из очереди немедленно"""
    try:
        post_data = post_storage.get_scheduled_post(post_id)
        if not post_data:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

        # Публикуем пост
        from services.publisher import publish_post_now
        success = await publish_post_now(post_data)

        if success:
            post_storage.mark_post_published(post_id)
            await callback.message.edit_text(
                text=f"✅ **ПОСТ ОПУБЛИКОВАН**\n\n"
                     f"Пост #{post_id} успешно опубликован!",
                reply_markup=create_back_to_menu_keyboard(),
                parse_mode="Markdown"
            )
            await callback.answer("✅ Пост опубликован!")
            logger.info(f"Пост #{post_id} опубликован из очереди")
        else:
            await callback.answer("❌ Ошибка публикации", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка публикации поста из очереди: {e}")
        await callback.answer("❌ Ошибка публикации", show_alert=True)


async def handle_queue_change_time(callback: CallbackQuery, post_id: int, state: FSMContext):
    """Изменяет время публикации поста из очереди"""
    try:
        post_data = post_storage.get_scheduled_post(post_id)
        if not post_data:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

        # Переводим в режим изменения времени
        await state.set_state(PostCreation.scheduling)
        await state.update_data(rescheduling_post_id=post_id)

        current_time = time_slot_manager.format_datetime_for_user(post_data['publish_time'])

        change_text = (
            f"⏰ **ИЗМЕНЕНИЕ ВРЕМЕНИ ПОСТА #{post_id}**\n\n"
            f"Текущее время: **{current_time}**\n\n"
            f"Выберите новое время:"
        )

        await callback.message.edit_text(
            text=change_text,
            reply_markup=create_simple_scheduler_keyboard(post_id),
            parse_mode="Markdown"
        )
        await callback.answer("⏰ Выберите новое время")

    except Exception as e:
        logger.error(f"Ошибка изменения времени: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


async def handle_queue_cancel(callback: CallbackQuery, post_id: int, state: FSMContext):
    """Отменяет публикацию поста"""
    try:
        success = post_storage.cancel_scheduled_post(post_id)

        if success:
            await callback.message.edit_text(
                text=f"❌ **ПУБЛИКАЦИЯ ОТМЕНЕНА**\n\n"
                     f"Пост #{post_id} удален из очереди.",
                reply_markup=create_back_to_menu_keyboard(),
                parse_mode="Markdown"
            )
            await callback.answer("❌ Публикация отменена")
            logger.info(f"Публикация поста #{post_id} отменена")
        else:
            await callback.answer("❌ Ошибка отмены", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка отмены публикации: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# =============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================

def find_next_available_slot(target_time: datetime) -> datetime:
    """Находит следующий доступный слот после указанного времени"""
    current = target_time
    weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # Ищем в течение 7 дней
    for days_ahead in range(7):
        check_date = current + timedelta(days=days_ahead)
        weekday = check_date.weekday()
        day_name = weekday_names[weekday]

        day_schedule = POSTING_SCHEDULE.get(day_name, [])

        for slot in day_schedule:
            start_time = datetime.strptime(slot['start'], '%H:%M').time()
            end_time = datetime.strptime(slot['end'], '%H:%M').time()

            slot_start = check_date.replace(
                hour=start_time.hour,
                minute=start_time.minute,
                second=0,
                microsecond=0
            )

            # Проверяем переход через полночь
            if end_time < start_time:
                slot_end = slot_start + timedelta(hours=24)
                slot_end = slot_end.replace(hour=end_time.hour, minute=end_time.minute)
            else:
                slot_end = check_date.replace(
                    hour=end_time.hour,
                    minute=end_time.minute,
                    second=0,
                    microsecond=0
                )

            # Если слот начинается после целевого времени
            if slot_start > target_time:
                # Генерируем случайное время в слоте
                slot_duration = (slot_end - slot_start).total_seconds()
                random_offset = random.randint(0, int(slot_duration) // 60)  # В минутах
                return slot_start + timedelta(minutes=random_offset)

    return None Пустое действие (декоративные кнопки)
            await callback.answer()
            return

        elif action == "day_morning":
            # Планирование на день утром (упрощенный вариант)
            await handle_day_schedule(callback, post_id, day, "morning", state)

        elif action == "quick_time":
            # Быстрый выбор времени (утро/вечер/ночь)
            await handle_quick_time_selection(callback, post_id, time_slot, state)

        elif action == "quick":
            # Очень быстрый выбор (30 мин, 1 час)
            await handle_very_quick_schedule(callback, post_id, time_slot, state)

        else:
            logger.warning(f"Неизвестное действие планировщика: {action}")
            await callback.answer("❌ Неизвестное действие", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка обработки действия планировщика {action}: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def handle_day_schedule(callback: CallbackQuery, post_id: int, selected_day: str, time_period: str,
                              state: FSMContext):
    """Планирует пост на конкретный день в определенное время"""
    try:
        # Находим следующий такой день
        now = datetime.now()
        weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        target_weekday = weekday_names.index(selected_day)

        # Ищем ближайший такой день недели
        current_weekday = now.weekday()
        days_ahead = (target_weekday - current_weekday) % 7

        if days_ahead == 0:
            days_ahead = 7  # Следующая неделя если сегодня тот же день

        target_date = now + timedelta(days=days_ahead)

        # Получаем расписание для дня
        day_schedule = POSTING_SCHEDULE.get(selected_day, [])
        if not day_schedule:
            await callback.answer("❌ Нет расписания для этого дня", show_alert=True)
            return

        # Выбираем случайный слот из доступных
        slot = random.choice(day_schedule)

        # Генерируем случайное время в пределах слота
        start_time = datetime.strptime(slot['start'], '%H:%M').time()
        end_time = datetime.strptime(slot['end'], '%H:%M').time()

        # Обработка перехода через полночь
        if end_time < start_time:
            end_hour = end_time.hour + 24
        else:
            end_hour = end_time.hour

        # Генерируем случайное время
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_hour * 60 + end_time.minute

        random_minutes = random.randint(start_minutes, end_minutes - 1)
        random_hour = random_minutes // 60
        random_minute = random_minutes % 60

        # Обработка перехода через полночь
        if random_hour >= 24:
            random_hour -= 24
            target_date += timedelta(days=1)

        schedule_time = target_date.replace(
            hour=random_hour,
            minute=random_minute,
            second=0,
            microsecond=0
        )

        await schedule_post_and_finish(callback, post_id, schedule_time, state)

    except Exception as e:
        logger.error(f"Ошибка планирования на день: {e}")
        await callback.answer("❌ Ошибка планирования", show_alert=True)


async def handle_quick_time_selection(callback: CallbackQuery, post_id: int, time_slot: str, state: FSMContext):
    """Обрабатывает быстрый выбор времени (утро/вечер/ночь)"""
    try:
        now = datetime.now()
        schedule_time = None

        time_ranges = {
            'morning': (10, 12),  # 10:00-12:00
            'evening': (19, 22),  # 19:00-22:00
            'night': (23, 1)  # 23:00-01:00
        }

        if time_slot not in time_ranges:
            await callback.answer("❌ Неизвестный временной слот", show_alert=True)
            return

        start_hour, end_hour = time_ranges[time_slot]

        # Ищем ближайший подходящий день
        for days_ahead in range(7):
            check_date = now + timedelta(days=days_ahead)
            weekday = check_date.weekday()

            weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            day_name = weekday_names[weekday]

            day_schedule = POSTING_SCHEDULE.get(day_name, [])

            for slot in day_schedule:
                slot_start_hour = int(slot['start'].split(':')[0])
                slot_end_hour = int(slot['end'].split(':')[0])

                # Обработка перехода через полночь
                if slot_end_hour < slot_start_hour:
                    slot_end_hour += 24

                # Проверяем пересечение с нужным временем
                if time_slot == 'night' and start_hour == 23:
                    if (slot_start_hour >= 23 or slot_end_hour <= 1 or
                            (slot_start_hour <= 23 and slot_end_hour >= 24)):
                        if slot_start_hour >= 23:
                            random_hour = random.randint(23, min(23, slot_end_hour))
                        else:
                            random_hour = random.randint(max(0, slot_start_hour), min(1, slot_end_hour))

                        random_minute = random.randint(0, 59)
                        schedule_time = check_date.replace(hour=random_hour, minute=random_minute, second=0,
                                                           microsecond=0)
                        break
                else:
                    if (slot_start_hour <= start_hour and slot_end_hour >= end_hour) or \
                            (slot_start_hour < end_hour and slot_end_hour > start_hour):
                        actual_start = max(slot_start_hour, start_hour)
                        actual_end = min(slot_end_hour, end_hour)

                        if actual_start < actual_end:
                            random_hour = random.randint(actual_start, actual_end - 1)
                            random_minute = random.randint(0, 59)
                            schedule_time = check_date.replace(hour=random_hour, minute=random_minute, second=0,
                                                               microsecond=0)
                            break

            if schedule_time:
                # Проверяем, что время не в прошлом
                if schedule_time > now:
                    break
                else:
                    schedule_time = None

        if not schedule_time:
            await callback.answer("❌ Не найдено подходящее время в расписании", show_alert=True)
            return

        await schedule_post_and_finish(callback, post_id, schedule_time, state)

    except Exception as e:
        logger.error(f"Ошибка быстрого выбора времени: {e}")
        await callback.answer("❌ Ошибка планирования", show_alert=True)


async def handle_very_quick_schedule(callback: CallbackQuery, post_id: int, time_slot: str, state: FSMContext):
    """Обрабатывает очень быстрое планирование (30 мин, 1 час)"""
    try:
        now = datetime.now()

        if time_slot == "30min":
            target_time = now + timedelta(minutes=30)
        elif time_slot == "1hour":
            target_time = now + timedelta(hours=1)
        else:
            await callback.answer("❌ Неизвестная опция", show_alert=True)
            return

        # Находим ближайший доступный слот
        schedule_time = find_next_available_slot(target_time)

        if not schedule_time:
            await callback.answer("❌ Нет доступных слотов", show_alert=True)
            return

        await schedule_post_and_finish(callback, post_id, schedule_time, state)

    except Exception as e:
        logger.error(f"Ошибка быстрого планирования: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


async def schedule_post_and_finish(callback: CallbackQuery, post_id: int, schedule_time: datetime, state: FSMContext):
    """Завершает планирование поста"""
    try:
        # Получаем данные поста
        post_data = post_storage.get_pending_post(post_id)
        if not post_data:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

        #