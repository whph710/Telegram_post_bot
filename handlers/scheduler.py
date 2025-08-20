# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from states import PostCreation, Menu
from keyboards import (
    ScheduleAction, QueueAction,
    create_scheduler_keyboard, create_back_to_menu_keyboard,
    create_queue_item_keyboard
)
from config import ADMIN_ID, MESSAGES
from utils.post_storage import post_storage
from utils.time_slots import time_slot_manager

router = Router()
logger = logging.getLogger(__name__)


async def show_scheduler(callback: CallbackQuery, state: FSMContext, post_id: int):
    """Показывает планировщик времени"""
    await state.set_state(PostCreation.scheduling)

    # Сохраняем ID поста в контекст состояния
    await state.update_data(scheduling_post_id=post_id)

    schedule_text = (
        f"⏰ **ПЛАНИРОВАНИЕ ПОСТА #{post_id}**\n\n"
        f"Выберите когда опубликовать пост:\n\n"
        f"📋 **Расписание постинга:**\n"
        f"{time_slot_manager.get_schedule_summary()}"
    )

    await callback.message.edit_text(
        text=schedule_text,
        reply_markup=create_scheduler_keyboard(post_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(ScheduleAction.filter())
async def handle_schedule_action(callback: CallbackQuery, callback_data: ScheduleAction, state: FSMContext):
    """Обработчик действий планировщика"""
    action = callback_data.action
    post_id = callback_data.post_id
    option = callback_data.option

    logger.info(f"Получено действие планировщика: {action}, post_id: {post_id}, option: {option}")

    # Получаем пост
    post_data = post_storage.get_pending_post(post_id)
    if not post_data:
        await callback.answer("❌ Пост не найден", show_alert=True)
        logger.warning(f"Пост #{post_id} не найден при планировании")
        return

    try:
        if action == "quick":
            # Быстрое планирование
            await handle_quick_schedule(callback, post_id, option, state)

        elif action == "custom":
            # Пользовательское время
            await handle_custom_time_request(callback, post_id, state)

        elif action == "distribute":
            # Автоматическое распределение
            await handle_auto_distribute(callback, post_id, state)

        else:
            logger.warning(f"Неизвестное действие планировщика: {action}")
            await callback.answer("❌ Неизвестное действие", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка обработки действия планировщика {action}: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


async def handle_quick_schedule(callback: CallbackQuery, post_id: int, option: str, state: FSMContext):
    """Обработка быстрого планирования"""
    try:
        # Получаем время для опции
        schedule_time = time_slot_manager.get_quick_schedule_time(option, datetime.now())

        if not schedule_time:
            await callback.answer("❌ Не удалось найти подходящее время", show_alert=True)
            return

        # Получаем данные поста
        post_data = post_storage.get_pending_post(post_id)
        if not post_data:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

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
            text=MESSAGES['post_scheduled'].format(time=formatted_time),
            reply_markup=create_back_to_menu_keyboard()
        )
        await callback.answer(f"✅ Пост запланирован на {formatted_time}")

        # Возвращаем в главное меню
        await state.set_state(Menu.main)
        logger.info(f"Пост #{post_id} запланирован на {schedule_time} (быстрое планирование)")

    except Exception as e:
        logger.error(f"Ошибка быстрого планирования: {e}")
        await callback.answer("❌ Ошибка планирования", show_alert=True)


async def handle_custom_time_request(callback: CallbackQuery, post_id: int, state: FSMContext):
    """Запрос пользовательского времени"""
    await state.update_data(scheduling_post_id=post_id)

    custom_time_text = (
        f"⏰ **ПОЛЬЗОВАТЕЛЬСКОЕ ВРЕМЯ**\n\n"
        f"Отправьте дату и время в формате:\n"
        f"`ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
        f"Примеры:\n"
        f"• `25.12.2024 14:30`\n"
        f"• `01.01.2025 09:00`\n\n"
        f"⚠️ Время должно попадать в разрешенные слоты для постинга"
    )

    await callback.message.edit_text(
        text=custom_time_text,
        reply_markup=create_back_to_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("📝 Отправьте дату и время")


async def handle_auto_distribute(callback: CallbackQuery, post_id: int, state: FSMContext):
    """Автоматическое распределение в ближайшие слоты"""
    try:
        # Получаем данные поста
        post_data = post_storage.get_pending_post(post_id)
        if not post_data:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return

        # Находим ближайший доступный слот
        now = datetime.now()
        next_slot = time_slot_manager.get_next_available_slot(now + timedelta(minutes=30))

        if not next_slot:
            await callback.answer("❌ Не найдено доступных слотов", show_alert=True)
            return

        # Планируем пост
        scheduled_id = post_storage.schedule_post(
            processed_text=post_data['processed_text'],
            publish_time=next_slot,
            user_id=post_data['user_id'],
            original_message=post_data.get('original_message'),
            original_messages=post_data.get('original_messages')
        )

        # Удаляем из ожидающих
        post_storage.remove_pending_post(post_id)

        # Форматируем время для пользователя
        formatted_time = time_slot_manager.format_datetime_for_user(next_slot)

        await callback.message.edit_text(
            text=f"🔄 **АВТОРАСПРЕДЕЛЕНИЕ**\n\n"
                 f"Пост автоматически запланирован на ближайшее доступное время:\n\n"
                 f"📅 **{formatted_time}**",
            reply_markup=create_back_to_menu_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer(f"✅ Пост запланирован на {formatted_time}")

        # Возвращаем в главное меню
        await state.set_state(Menu.main)
        logger.info(f"Пост #{post_id} автоматически запланирован на {next_slot}")

    except Exception as e:
        logger.error(f"Ошибка автораспределения: {e}")
        await callback.answer("❌ Ошибка планирования", show_alert=True)


@router.message(StateFilter(PostCreation.scheduling), F.from_user.id == ADMIN_ID)
async def handle_custom_time_input(message: Message, state: FSMContext):
    """Обработка ввода пользовательского времени"""
    try:
        # Получаем ID поста из состояния
        data = await state.get_data()
        post_id = data.get('scheduling_post_id')
        rescheduling_post_id = data.get('rescheduling_post_id')

        if rescheduling_post_id:
            # Это перепланирование существующего поста
            await handle_reschedule_post(message, rescheduling_post_id, state)
            return

        if not post_id:
            await message.reply("❌ Ошибка: ID поста не найден")
            await state.set_state(Menu.main)
            return

        # Получаем данные поста
        post_data = post_storage.get_pending_post(post_id)
        if not post_data:
            await message.reply("❌ Пост не найден")
            await state.set_state(Menu.main)
            return

        # Парсим время
        custom_time = time_slot_manager.parse_user_datetime(message.text)

        if not custom_time:
            await message.reply(
                "❌ Неверный формат даты/времени или время в прошлом\n\n"
                "Используйте формат: `ДД.ММ.ГГГГ ЧЧ:ММ`",
                parse_mode="Markdown"
            )
            return

        # Проверяем, попадает ли в слоты
        if not time_slot_manager.is_time_in_slots(custom_time):
            # Находим ближайший доступный слот
            nearest_slot = time_slot_manager.get_next_available_slot(custom_time)

            if nearest_slot:
                formatted_nearest = time_slot_manager.format_datetime_for_user(nearest_slot)
                await message.reply(
                    f"⚠️ Указанное время не попадает в разрешенные слоты\n\n"
                    f"Ближайшее доступное время: **{formatted_nearest}**\n\n"
                    f"Используем это время.",
                    parse_mode="Markdown"
                )
                custom_time = nearest_slot
            else:
                await message.reply("❌ Не найдено доступных слотов в ближайшее время")
                return

        # Планируем пост
        scheduled_id = post_storage.schedule_post(
            processed_text=post_data['processed_text'],
            publish_time=custom_time,
            user_id=post_data['user_id'],
            original_message=post_data.get('original_message'),
            original_messages=post_data.get('original_messages')
        )

        # Удаляем из ожидающих
        post_storage.remove_pending_post(post_id)

        # Форматируем время для пользователя
        formatted_time = time_slot_manager.format_datetime_for_user(custom_time)

        await message.reply(
            f"✅ **ПОСТ ЗАПЛАНИРОВАН**\n\n"
            f"📅 Время публикации: **{formatted_time}**\n\n"
            f"Пост будет автоматически опубликован в указанное время.",
            parse_mode="Markdown"
        )

        # Возвращаем в главное меню
        await state.set_state(Menu.main)
        logger.info(f"Пост #{post_id} запланирован пользователем на {custom_time}")

    except Exception as e:
        logger.error(f"Ошибка обработки пользовательского времени: {e}")
        await message.reply("❌ Произошла ошибка при планировании")
        await state.set_state(Menu.main)


# Обработчики для очереди постов
@router.callback_query(QueueAction.filter())
async def handle_queue_action(callback: CallbackQuery, callback_data: QueueAction, state: FSMContext):
    """Обработчик действий с очередью"""
    action = callback_data.action
    post_id = callback_data.post_id

    logger.info(f"Получено действие с очередью: {action}, post_id: {post_id}")

    try:
        if action == "refresh":
            # Обновление списка очереди - переход к обработчику в menu.py
            from handlers.menu import show_queue
            await show_queue(callback, state)

        elif action == "publish_now" and post_id:
            # Публикация поста немедленно из очереди
            await handle_queue_publish_now(callback, post_id, state)

        elif action == "change_time" and post_id:
            # Изменение времени поста
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
            f"Отправьте новое время в формате:\n"
            f"`ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
            f"Или выберите быстрый вариант:"
        )

        await callback.message.edit_text(
            text=change_text,
            reply_markup=create_scheduler_keyboard(post_id),
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


async def handle_reschedule_post(message: Message, post_id: int, state: FSMContext):
    """Обрабатывает перепланирование существующего поста"""
    try:
        # Получаем данные поста
        post_data = post_storage.get_scheduled_post(post_id)
        if not post_data:
            await message.reply("❌ Пост не найден")
            await state.set_state(Menu.main)
            return

        # Парсим новое время
        new_time = time_slot_manager.parse_user_datetime(message.text)

        if not new_time:
            await message.reply(
                "❌ Неверный формат даты/времени или время в прошлом\n\n"
                "Используйте формат: `ДД.ММ.ГГГГ ЧЧ:ММ`",
                parse_mode="Markdown"
            )
            return

        # Проверяем слоты
        if not time_slot_manager.is_time_in_slots(new_time):
            nearest_slot = time_slot_manager.get_next_available_slot(new_time)
            if nearest_slot:
                formatted_nearest = time_slot_manager.format_datetime_for_user(nearest_slot)
                await message.reply(
                    f"⚠️ Время не в слотах. Используем ближайшее: **{formatted_nearest}**",
                    parse_mode="Markdown"
                )
                new_time = nearest_slot
            else:
                await message.reply("❌ Нет доступных слотов")
                return

        # Обновляем время поста
        post_storage.update_scheduled_post(post_id, publish_time=new_time)

        formatted_time = time_slot_manager.format_datetime_for_user(new_time)

        await message.reply(
            f"✅ **ВРЕМЯ ИЗМЕНЕНО**\n\n"
            f"Пост #{post_id} перенесен на: **{formatted_time}**",
            parse_mode="Markdown"
        )

        await state.set_state(Menu.main)
        logger.info(f"Пост #{post_id} перепланирован на {new_time}")

    except Exception as e:
        logger.error(f"Ошибка перепланирования поста: {e}")
        await message.reply("❌ Ошибка перепланирования")
        await state.set_state(Menu.main)


# Обработка неизвестных callback'ов в планировщике
@router.callback_query(StateFilter(PostCreation.scheduling))
async def handle_unknown_scheduler_callback(callback: CallbackQuery):
    """Обработка неизвестных callback'ов в планировщике"""
    logger.warning(f"Неизвестный callback в планировщике: {callback.data}")
    await callback.answer("❌ Неизвестное действие", show_alert=True)