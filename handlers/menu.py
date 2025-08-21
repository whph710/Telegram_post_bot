# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from states import Menu, PostCreation, QueueView, Settings
from keyboards import (
    MenuAction, create_main_menu, create_settings_keyboard,
    create_queue_keyboard, create_back_to_menu_keyboard
)
from config import ADMIN_ID, MESSAGES, GROUP_ID
from utils.post_storage import post_storage
from utils.time_slots import time_slot_manager

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start", "menu"))
@router.message(F.text.in_(["Меню", "В меню", "/menu"]))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команд /start и /menu"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к этому боту")
        return

    await state.set_state(Menu.main)

    await message.answer(
        text=MESSAGES['start_welcome'],
        reply_markup=create_main_menu()
    )


@router.callback_query(MenuAction.filter(F.action == "main"))
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.set_state(Menu.main)

    await callback.message.edit_text(
        text=MESSAGES['start_welcome'],
        reply_markup=create_main_menu()
    )
    await callback.answer()


@router.callback_query(MenuAction.filter(F.action == "create_post"))
async def start_post_creation(callback: CallbackQuery, state: FSMContext):
    """Запуск создания поста"""
    await state.set_state(PostCreation.waiting)

    await callback.message.edit_text(
        text=MESSAGES['post_creation_prompt'],
        reply_markup=create_back_to_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(MenuAction.filter(F.action == "auto_mode_info"))
async def show_auto_mode_info(callback: CallbackQuery):
    """Показ информации об автоматическом режиме"""
    info_text = (
        f"🔄 **РЕЖИМ AUTO АКТИВЕН**\n\n"
        f"Просто отправьте любое сообщение боту (текст, медиа, альбом) "
        f"— он автоматически:\n\n"
        f"• Срежет ссылки на Telegram-каналы\n"
        f"• Уберет упоминания (@username)\n"
        f"• Отформатирует для группы\n"
        f"• Добавит подпись канала\n"
        f"• Покажет превью для подтверждения\n\n"
        f"📋 **Расписание постинга:**\n"
        f"{time_slot_manager.get_schedule_summary()}\n\n"
        f"Текущая группа: `{GROUP_ID}`"
    )

    await callback.message.edit_text(
        text=info_text,
        reply_markup=create_back_to_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(MenuAction.filter(F.action == "settings"))
async def show_settings(callback: CallbackQuery, state: FSMContext):
    """Показ настроек"""
    await state.set_state(Settings.main)

    # Получаем информацию об админе
    admin_username = "admin"  # Заглушка
    admin_id = ADMIN_ID
    group_name = f"Группа {GROUP_ID}"  # Заглушка

    settings_text = (
        f"⚙️ **НАСТРОЙКИ БОТА**\n\n"
        f"👤 Текущий админ: @{admin_username} ({admin_id})\n"
        f"📢 Группа для постов: {group_name}\n"
        f"ID: `{GROUP_ID}`\n\n"
        f"Выберите что настроить:"
    )

    await callback.message.edit_text(
        text=settings_text,
        reply_markup=create_settings_keyboard(
            admin_username=admin_username,
            admin_id=admin_id,
            group_name=group_name,
            group_id=GROUP_ID
        ),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(MenuAction.filter(F.action == "queue"))
async def show_queue(callback: CallbackQuery, state: FSMContext):
    """Показ очереди постов"""
    await state.set_state(QueueView.viewing)

    try:
        scheduled_posts = post_storage.get_scheduled_posts(limit=10)
    except Exception as e:
        logger.error(f"Ошибка получения очереди постов: {e}")
        scheduled_posts = []

    if not scheduled_posts:
        await callback.message.edit_text(
            text=MESSAGES['queue_empty'],
            reply_markup=create_back_to_menu_keyboard()
        )
        await callback.answer()
        return

    # Формируем список постов
    queue_text_lines = [
        MESSAGES['queue_title'].format(count=len(scheduled_posts)),
        ""
    ]

    for idx, post in enumerate(scheduled_posts, 1):
        # Обрезаем текст поста для превью
        post_preview = post['processed_text'][:50] if post['processed_text'] else "Без текста"
        if len(post.get('processed_text', '')) > 50:
            post_preview += "..."

        try:
            formatted_time = time_slot_manager.format_datetime_for_user(post['publish_time'])
        except Exception as e:
            logger.error(f"Ошибка форматирования времени для поста {post.get('id')}: {e}")
            formatted_time = "Ошибка времени"

        queue_text_lines.append(
            f"📅 {idx}. {formatted_time}\n"
            f"   \"{post_preview}\"\n"
        )

    queue_text = "\n".join(queue_text_lines)

    # Ограничиваем длину сообщения
    if len(queue_text) > 4000:
        queue_text = queue_text[:3900] + "\n\n... (список обрезан)"

    await callback.message.edit_text(
        text=queue_text,
        reply_markup=create_queue_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# Обработка неизвестных callback'ов в меню
@router.callback_query(StateFilter(Menu.main))
async def handle_unknown_menu_callback(callback: CallbackQuery):
    """Обработка неизвестных callback'ов в главном меню"""
    logger.warning(f"Неизвестный callback в главном меню: {callback.data}")
    await callback.answer("❌ Неизвестное действие", show_alert=True)