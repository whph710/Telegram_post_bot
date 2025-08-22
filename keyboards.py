# -*- coding: utf-8 -*-
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import List, Optional
from config import BUTTONS


# =============================================
# CALLBACK DATA КЛАССЫ
# =============================================

class MenuAction(CallbackData, prefix="menu"):
    action: str


class PostAction(CallbackData, prefix="post"):
    action: str
    post_id: int


class ScheduleAction(CallbackData, prefix="schedule"):
    action: str
    post_id: int
    day: Optional[str] = None
    time_slot: Optional[str] = None


class QueueAction(CallbackData, prefix="queue"):
    action: str
    post_id: Optional[int] = None


class SettingsAction(CallbackData, prefix="settings"):
    action: str
    prompt_type: Optional[str] = None


class PromptAction(CallbackData, prefix="prompt"):
    action: str
    prompt_type: str


class AdminAction(CallbackData, prefix="admin"):
    action: str
    admin_id: Optional[int] = None


# =============================================
# ГЛАВНОЕ МЕНЮ
# =============================================

def create_main_menu() -> InlineKeyboardMarkup:
    """Создает главное меню"""
    try:
        from utils.post_storage import post_storage
        scheduled_count = len(post_storage.get_scheduled_posts())
    except Exception:
        scheduled_count = 0

    buttons = [
        [InlineKeyboardButton(
            text=BUTTONS['create_post'],
            callback_data=MenuAction(action="create_post").pack()
        )],
        [
            InlineKeyboardButton(
                text="──── СИСТЕМА ────",
                callback_data=SettingsAction(action="none").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['change_admin'],
                callback_data=SettingsAction(action="change_admin").pack()
            ),
            InlineKeyboardButton(
                text=BUTTONS['change_group'],
                callback_data=SettingsAction(action="change_group").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['show_stats'],
                callback_data=SettingsAction(action="stats").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['back_to_menu'],
                callback_data=MenuAction(action="main").pack()
            )
        ]
    ])


# =============================================
# РЕДАКТИРОВАНИЕ ПРОМПТОВ
# =============================================

def create_prompt_edit_keyboard(prompt_type: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для редактирования промпта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS['view_current_prompt'],
                callback_data=PromptAction(action="view", prompt_type=prompt_type).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['edit_prompt'],
                callback_data=PromptAction(action="edit", prompt_type=prompt_type).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['reset_prompt'],
                callback_data=PromptAction(action="reset", prompt_type=prompt_type).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['back_to_settings'],
                callback_data=MenuAction(action="settings").pack()
            )
        ]
    ])


# =============================================
# ПОДТВЕРЖДЕНИЯ
# =============================================

def create_admin_confirm_keyboard(new_admin_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения смены админа"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS['confirm_yes'],
                callback_data=AdminAction(action="confirm", admin_id=new_admin_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['confirm_no'],
                callback_data=MenuAction(action="settings").pack()
            )
        ]
    ])


def create_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает простую клавиатуру с кнопкой "Назад в меню" """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS['back_to_menu'],
                callback_data=MenuAction(action="main").pack()
            )
        ]
    ])


def create_back_to_settings_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой "Назад к настройкам" """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS['back_to_settings'],
                callback_data=MenuAction(action="settings").pack()
            )
        ]
    ])(
                text=BUTTONS['auto_mode'],
                callback_data=MenuAction(action="auto_mode_info").pack()
            ),
            InlineKeyboardButton(
                text=BUTTONS['settings'],
                callback_data=MenuAction(action="settings").pack()
            )
        ]
    ]

    # Добавляем кнопку очереди с количеством
    if scheduled_count > 0:
        queue_text = f"📋 Очередь ({scheduled_count})"
    else:
        queue_text = "📋 Очередь"

    buttons.append([
        InlineKeyboardButton(
            text=queue_text,
            callback_data=MenuAction(action="queue").pack()
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =============================================
# ПРЕВЬЮ ПОСТА
# =============================================

def create_post_preview_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для превью поста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS['publish_now'],
                callback_data=PostAction(action="publish", post_id=post_id).pack()
            ),
            InlineKeyboardButton(
                text=BUTTONS['schedule_post'],
                callback_data=PostAction(action="schedule", post_id=post_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['improve_post'],
                callback_data=PostAction(action="edit", post_id=post_id).pack()
            ),
            InlineKeyboardButton(
                text=BUTTONS['delete_post'],
                callback_data=PostAction(action="delete", post_id=post_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['back_to_menu'],
                callback_data=MenuAction(action="main").pack()
            )
        ]
    ])


# =============================================
# УПРОЩЕННЫЙ ПЛАНИРОВЩИК
# =============================================

def create_simple_scheduler_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Создает упрощенный планировщик"""
    return InlineKeyboardMarkup(inline_keyboard=[
        # Дни недели
        [
            InlineKeyboardButton(
                text="ПН",
                callback_data=ScheduleAction(action="day_morning", post_id=post_id, day="monday").pack()
            ),
            InlineKeyboardButton(
                text="ВТ",
                callback_data=ScheduleAction(action="day_morning", post_id=post_id, day="tuesday").pack()
            ),
            InlineKeyboardButton(
                text="СР",
                callback_data=ScheduleAction(action="day_morning", post_id=post_id, day="wednesday").pack()
            ),
            InlineKeyboardButton(
                text="ЧТ",
                callback_data=ScheduleAction(action="day_morning", post_id=post_id, day="thursday").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="ПТ",
                callback_data=ScheduleAction(action="day_morning", post_id=post_id, day="friday").pack()
            ),
            InlineKeyboardButton(
                text="СБ",
                callback_data=ScheduleAction(action="day_morning", post_id=post_id, day="saturday").pack()
            ),
            InlineKeyboardButton(
                text="ВС",
                callback_data=ScheduleAction(action="day_morning", post_id=post_id, day="sunday").pack()
            )
        ],
        # Разделитель
        [
            InlineKeyboardButton(
                text="───── ВРЕМЯ ДНЯ ─────",
                callback_data=ScheduleAction(action="none", post_id=post_id).pack()
            )
        ],
        # Время суток
        [
            InlineKeyboardButton(
                text="🌅 Утро (10:00-12:00)",
                callback_data=ScheduleAction(action="quick_time", post_id=post_id, time_slot="morning").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="🌆 Вечер (19:00-22:00)",
                callback_data=ScheduleAction(action="quick_time", post_id=post_id, time_slot="evening").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="🌙 Ночь (23:00-01:00)",
                callback_data=ScheduleAction(action="quick_time", post_id=post_id, time_slot="night").pack()
            )
        ],
        # Быстрые варианты
        [
            InlineKeyboardButton(
                text="⚡ Через 30 мин",
                callback_data=ScheduleAction(action="quick", post_id=post_id, time_slot="30min").pack()
            ),
            InlineKeyboardButton(
                text="🕐 Через 1 час",
                callback_data=ScheduleAction(action="quick", post_id=post_id, time_slot="1hour").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['back_to_menu'],
                callback_data=MenuAction(action="main").pack()
            )
        ]
    ])


# =============================================
# ОЧЕРЕДЬ ПОСТОВ
# =============================================

def create_queue_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для очереди постов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS['refresh_queue'],
                callback_data=QueueAction(action="refresh").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['back_to_menu'],
                callback_data=MenuAction(action="main").pack()
            )
        ]
    ])


def create_queue_item_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для элемента очереди"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BUTTONS['publish_now_queue'],
                callback_data=QueueAction(action="publish_now", post_id=post_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['change_time'],
                callback_data=QueueAction(action="change_time", post_id=post_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['cancel_publication'],
                callback_data=QueueAction(action="cancel", post_id=post_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['back_to_menu'],
                callback_data=MenuAction(action="main").pack()
            )
        ]
    ])


# =============================================
# НАСТРОЙКИ
# =============================================

def create_settings_keyboard(admin_username: str, admin_id: int, group_name: str,
                             group_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру настроек"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="──── ПРОМПТЫ ────",
                callback_data=SettingsAction(action="none").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['edit_style_prompt'],
                callback_data=SettingsAction(action="edit_prompt", prompt_type="style_formatting").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['edit_group_prompt'],
                callback_data=SettingsAction(action="edit_prompt", prompt_type="group_processing").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text=BUTTONS['edit_improve_prompt'],
                callback_data=SettingsAction(action="edit_prompt", prompt_type="post_improvement").pack()
            )
        ],
        [
            InlineKeyboardButton