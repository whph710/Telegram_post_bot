# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from states import Settings, Menu
from keyboards import (
    SettingsAction, PromptAction, AdminAction,
    create_settings_keyboard, create_prompt_edit_keyboard,
    create_admin_confirm_keyboard, create_back_to_settings_keyboard,
    create_back_to_menu_keyboard
)
from config import ADMIN_ID, MESSAGES, PROMPT_NAMES, GROUP_ID
from services.ai_processor import ai_processor
from utils.post_storage import post_storage

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(SettingsAction.filter(F.action == "none"))
async def handle_empty_action(callback: CallbackQuery):
    """Обработка пустых действий (декоративные кнопки)"""
    await callback.answer()


@router.callback_query(SettingsAction.filter(F.action == "edit_prompt"))
async def show_prompt_editor(callback: CallbackQuery, callback_data: SettingsAction, state: FSMContext):
    """Показывает редактор промпта"""
    prompt_type = callback_data.prompt_type

    if not prompt_type or prompt_type not in PROMPT_NAMES:
        await callback.answer("❌ Неизвестный тип промпта", show_alert=True)
        return

    await state.set_state(Settings.main)

    prompt_name = PROMPT_NAMES[prompt_type]
    edit_text = (
        f"📝 **РЕДАКТИРОВАНИЕ ПРОМПТА**\n\n"
        f"**Тип:** {prompt_name}\n\n"
        f"Выберите действие:"
    )

    await callback.message.edit_text(
        text=edit_text,
        reply_markup=create_prompt_edit_keyboard(prompt_type),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(PromptAction.filter(F.action == "view"))
async def view_current_prompt(callback: CallbackQuery, callback_data: PromptAction):
    """Показывает текущий промпт"""
    prompt_type = callback_data.prompt_type

    try:
        prompt_content = await ai_processor.load_prompt(prompt_type)
        prompt_name = PROMPT_NAMES.get(prompt_type, prompt_type)

        # Обрезаем слишком длинный промпт
        if len(prompt_content) > 3000:
            prompt_content = prompt_content[:3000] + "\n\n... (обрезано)"

        view_text = (
            f"📖 **ТЕКУЩИЙ ПРОМПТ: {prompt_name}**\n\n"
            f"```\n{prompt_content}\n```"
        )

        await callback.message.edit_text(
            text=view_text,
            reply_markup=create_prompt_edit_keyboard(prompt_type),
            parse_mode="Markdown"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка просмотра промпта {prompt_type}: {e}")
        await callback.answer("❌ Ошибка загрузки промпта", show_alert=True)


@router.callback_query(PromptAction.filter(F.action == "edit"))
async def start_prompt_editing(callback: CallbackQuery, callback_data: PromptAction, state: FSMContext):
    """Начинает редактирование промпта"""
    prompt_type = callback_data.prompt_type

    await state.set_state(Settings.editing_prompt)
    await state.update_data(editing_prompt_type=prompt_type)

    prompt_name = PROMPT_NAMES.get(prompt_type, prompt_type)

    edit_text = (
        f"✏️ **РЕДАКТИРОВАНИЕ ПРОМПТА**\n\n"
        f"**Тип:** {prompt_name}\n\n"
        f"Отправьте новый текст промпта:"
    )

    await callback.message.edit_text(
        text=edit_text,
        reply_markup=create_back_to_settings_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("📝 Отправьте новый текст промпта")


@router.callback_query(PromptAction.filter(F.action == "reset"))
async def reset_prompt(callback: CallbackQuery, callback_data: PromptAction):
    """Сбрасывает промпт на стандартный"""
    prompt_type = callback_data.prompt_type

    try:
        # Получаем стандартный промпт
        default_prompt = ai_processor._get_default_prompt(prompt_type)

        # Сохраняем его
        success = await ai_processor.save_prompt(prompt_type, default_prompt)

        if success:
            prompt_name = PROMPT_NAMES.get(prompt_type, prompt_type)
            await callback.message.edit_text(
                text=f"✅ **ПРОМПТ СБРОШЕН**\n\n"
                     f"Промпт \"{prompt_name}\" сброшен на стандартный.",
                reply_markup=create_prompt_edit_keyboard(prompt_type),
                parse_mode="Markdown"
            )
            await callback.answer("✅ Промпт сброшен")
        else:
            await callback.answer("❌ Ошибка сброса промпта", show_alert=True)

    except Exception as e:
        logger.error(f"Ошибка сброса промпта {prompt_type}: {e}")
        await callback.answer("❌ Ошибка сброса", show_alert=True)


@router.message(StateFilter(Settings.editing_prompt), F.from_user.id == ADMIN_ID)
async def handle_prompt_edit(message: Message, state: FSMContext):
    """Обрабатывает новый текст промпта"""
    data = await state.get_data()
    prompt_type = data.get('editing_prompt_type')

    if not prompt_type:
        await message.reply("❌ Ошибка: тип промпта не найден")
        await state.set_state(Settings.main)
        return

    try:
        new_prompt_text = message.text.strip()

        if not new_prompt_text:
            await message.reply("❌ Промпт не может быть пустым")
            return

        # Сохраняем новый промпт
        success = await ai_processor.save_prompt(prompt_type, new_prompt_text)

        if success:
            prompt_name = PROMPT_NAMES.get(prompt_type, prompt_type)
            await message.reply(
                f"✅ **ПРОМПТ ОБНОВЛЕН**\n\n"
                f"Промпт \"{prompt_name}\" успешно обновлен!",
                parse_mode="Markdown"
            )
            await state.set_state(Settings.main)
        else:
            await message.reply("❌ Ошибка сохранения промпта")

    except Exception as e:
        logger.error(f"Ошибка сохранения промпта: {e}")
        await message.reply("❌ Ошибка сохранения")


@router.callback_query(SettingsAction.filter(F.action == "stats"))
async def show_stats(callback: CallbackQuery):
    """Показывает статистику бота"""
    try:
        stats = post_storage.get_stats()

        stats_text = (
            f"📊 **СТАТИСТИКА БОТА**\n\n"
            f"📝 Ожидающих постов: {stats['pending_posts']}\n"
            f"⏰ Запланированных постов: {stats['scheduled_posts']}\n"
            f"✅ Опубликованных постов: {stats['published_posts']}\n"
            f"📈 Всего обработано: {stats['total_processed']}\n\n"
            f"👤 Текущий админ: {ADMIN_ID}\n"
            f"📢 Группа: `{GROUP_ID}`"
        )

        await callback.message.edit_text(
            text=stats_text,
            reply_markup=create_back_to_settings_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)


@router.callback_query(SettingsAction.filter(F.action == "change_admin"))
async def start_admin_change(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс смены админа"""
    await state.set_state(Settings.changing_admin)

    change_text = (
        f"👤 **СМЕНА АДМИНА**\n\n"
        f"⚠️ **ВНИМАНИЕ:** После смены админа вы потеряете доступ к боту!\n\n"
        f"Отправьте ID нового админа (только цифры):"
    )

    await callback.message.edit_text(
        text=change_text,
        reply_markup=create_back_to_settings_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("👤 Отправьте ID нового админа")


@router.message(StateFilter(Settings.changing_admin), F.from_user.id == ADMIN_ID)
async def handle_admin_change(message: Message, state: FSMContext):
    """Обрабатывает смену админа"""
    try:
        new_admin_id = int(message.text.strip())

        if new_admin_id == ADMIN_ID:
            await message.reply("❌ Вы уже являетесь админом")
            return

        # Показываем подтверждение
        confirm_text = (
            f"⚠️ **ПОДТВЕРЖДЕНИЕ СМЕНЫ АДМИНА**\n\n"
            f"Новый админ: `{new_admin_id}`\n\n"
            f"**Вы уверены?** После подтверждения вы потеряете доступ к боту!"
        )

        await message.reply(
            text=confirm_text,
            reply_markup=create_admin_confirm_keyboard(new_admin_id),
            parse_mode="Markdown"
        )

    except ValueError:
        await message.reply("❌ Неверный формат ID. Отправьте только цифры.")
    except Exception as e:
        logger.error(f"Ошибка смены админа: {e}")
        await message.reply("❌ Ошибка обработки ID")


@router.callback_query(AdminAction.filter(F.action == "confirm"))
async def confirm_admin_change(callback: CallbackQuery, callback_data: AdminAction, state: FSMContext):
    """Подтверждает смену админа"""
    new_admin_id = callback_data.admin_id

    try:
        # В реальном боте здесь должно быть обновление конфига/БД
        # Пока что просто уведомляем

        await callback.message.edit_text(
            text=f"⚠️ **ФУНКЦИЯ В РАЗРАБОТКЕ**\n\n"
                 f"Смена админа на ID {new_admin_id} будет реализована в следующей версии.\n\n"
                 f"Для смены админа сейчас нужно изменить переменную ADMIN_ID в .env файле.",
            reply_markup=create_back_to_settings_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer("⚠️ Функция в разработке")
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка подтверждения смены админа: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(SettingsAction.filter(F.action == "change_group"))
async def start_group_change(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс смены группы"""
    await state.set_state(Settings.changing_group)

    change_text = (
        f"📢 **СМЕНА ГРУППЫ**\n\n"
        f"Текущая группа: `{GROUP_ID}`\n\n"
        f"Отправьте ID новой группы (начинается с -100):"
    )

    await callback.message.edit_text(
        text=change_text,
        reply_markup=create_back_to_settings_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("📢 Отправьте ID новой группы")


@router.message(StateFilter(Settings.changing_group), F.from_user.id == ADMIN_ID)
async def handle_group_change(message: Message, state: FSMContext):
    """Обрабатывает смену группы"""
    try:
        new_group_id = int(message.text.strip())

        if new_group_id == GROUP_ID:
            await message.reply("❌ Эта группа уже используется")
            return

        if not str(new_group_id).startswith('-100'):
            await message.reply("❌ ID группы должен начинаться с -100")
            return

        # В реальном боте здесь должна быть проверка доступа к группе
        await message.reply(
            text=f"⚠️ **ФУНКЦИЯ В РАЗРАБОТКЕ**\n\n"
                 f"Смена группы на ID {new_group_id} будет реализована в следующей версии.\n\n"
                 f"Для смены группы сейчас нужно изменить переменную GROUP_ID в .env файле.",
            parse_mode="Markdown"
        )

        await state.set_state(Settings.main)

    except ValueError:
        await message.reply("❌ Неверный формат ID. Отправьте только цифры.")
    except Exception as e:
        logger.error(f"Ошибка смены группы: {e}")
        await message.reply("❌ Ошибка обработки ID")


# ИСПРАВЛЕНО: Обработка возврата к настройкам через MenuAction
@router.callback_query(F.data == "menu:settings")
async def handle_back_to_settings_via_menu(callback: CallbackQuery, state: FSMContext):
    """Обработка возврата к настройкам через MenuAction"""
    await show_settings_from_callback(callback, state)


async def show_settings_from_callback(callback: CallbackQuery, state: FSMContext):
    """Вспомогательная функция для показа настроек"""
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


# Обработка неизвестных callback'ов в настройках
@router.callback_query(StateFilter(Settings))
async def handle_unknown_settings_callback(callback: CallbackQuery):
    """Обработка неизвестных callback'ов в настройках"""
    logger.warning(f"Неизвестный callback в настройках: {callback.data}")
    await callback.answer("❌ Неизвестное действие", show_alert=True)