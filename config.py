# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

# ===============================
# 🔑 API НАСТРОЙКИ
# ===============================
API_TOKEN = os.getenv("API_TOKEN")
GROUP_ID_STR = os.getenv("GROUP_ID")
ADMIN_ID_STR = os.getenv("MY_ID")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK")

# Проверяем и конвертируем ID
try:
    GROUP_ID = int(GROUP_ID_STR) if GROUP_ID_STR else None
except (ValueError, TypeError):
    GROUP_ID = None

try:
    ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR else None
except (ValueError, TypeError):
    ADMIN_ID = None

# ===============================
# ⏰ РАСПИСАНИЕ ПОСТИНГА (UTC+5)
# ===============================
POSTING_SCHEDULE = {
    'monday': [
        {'start': '10:00', 'end': '12:00'},
        {'start': '13:00', 'end': '16:00'}
    ],
    'tuesday': [
        {'start': '10:00', 'end': '12:00'},
        {'start': '19:00', 'end': '22:00'}
    ],
    'wednesday': [
        {'start': '10:00', 'end': '12:00'},
        {'start': '13:00', 'end': '16:00'}
    ],
    'thursday': [
        {'start': '10:00', 'end': '12:00'},
        {'start': '17:00', 'end': '22:00'}
    ],
    'friday': [
        {'start': '10:00', 'end': '12:00'},
        {'start': '17:00', 'end': '22:00'},
        {'start': '23:00', 'end': '01:00'}  # До 1 ночи следующего дня
    ],
    'saturday': [
        {'start': '13:00', 'end': '16:00'},
        {'start': '23:00', 'end': '02:00'}  # До 2 ночи следующего дня
    ],
    'sunday': [
        {'start': '00:00', 'end': '02:00'},  # С полуночи до 2 утра
        {'start': '12:00', 'end': '16:00'},
        {'start': '19:00', 'end': '22:00'}
    ]
}

# ===============================
# 📝 ПУТИ К ПРОМПТАМ
# ===============================
PROMPT_PATHS = {
    'style_formatting': 'prompts/prompt1.txt',  # Стиль и форматирование
    'group_processing': 'prompts/prompt2.txt',  # Обработка для группы
    'post_improvement': 'prompts/prompt3.txt'  # Доработка постов
}

# ===============================
# 💬 ТЕКСТЫ СООБЩЕНИЙ
# ===============================
MESSAGES = {
    'start_welcome': "🤖 Добро пожаловать!\n\nВыберите действие:",
    'post_creation_prompt': "📝 Отправьте текст и/или медиа для создания поста:",
    'auto_mode_status': "🔄 Режим: AUTO",
    'queue_empty': "📋 Очередь постов пуста",
    'queue_title': "📋 Отложенные посты ({count}):",
    'preview_title': "ПРЕДПРОСМОТР ПОСТА #{post_id}",
    'preview_footer': "--- КОНЕЦ ПОСТА ---",
    'post_published': "✅ Пост #{post_id} успешно опубликован!",
    'post_cancelled': "❌ Пост #{post_id} отменен",
    'post_deleted': "🗑 Пост удален",
    'post_scheduled': "⏰ Пост отложен на {time}",
    'settings_current_admin': "👤 Текущий админ: @{username} (ID: {user_id})",
    'settings_current_group': "📢 Группа для постов: {group_name}\nID: {group_id}",
    'editing_prompt_title': "📝 Редактирование: \"{prompt_name}\"",
    'prompt_updated': "✅ Промпт обновлен!",
    'time_input_prompt': "⏰ Отправьте дату и время в формате: ДД.ММ.ГГГГ ЧЧ:ММ",
    'new_admin_prompt': "👤 Отправьте ID нового админа (только цифры):",
    'new_group_prompt': "📢 Отправьте ID новой группы (начинается с -100):",
    'admin_change_confirm': "⚠️ Вы уверены? Вы потеряете доступ к боту!\nНовый админ: {new_admin_id}",
    'group_checking': "🧪 Проверяю доступ к группе...",
    'group_changed': "✅ Группа изменена!",
    'group_access_error': "❌ Нет доступа к группе",
    'edit_post_prompt': "✏️ Пост #{post_id} ожидает доработки.\n\nОтправьте сообщение с дополнениями:",
    'bot_started': "🤖 Бот запущен и готов к работе!",
    'bot_stopping': "🤖 Бот завершает работу...",
    'ai_processing_error': "❌ Ошибка обработки ИИ",
    'post_too_long_warning': "⚠️ Текст обрезан для медиа (лимит 1024 символа)",
    'input_truncated_warning': "⚠️ Входной текст может быть обрезан — проверь источник."
}

# ===============================
# 🎛 КНОПКИ ИНТЕРФЕЙСА
# ===============================
BUTTONS = {
    # Главное меню
    'create_post': "📝 Создать пост",
    'auto_mode': "🔄 Режим: AUTO",
    'settings': "⚙️ Настройки",
    'queue': "📋 Очередь ({count})",

    # Превью поста
    'publish_now': "✅ Запостить сейчас",
    'schedule_post': "⏰ Отложить пост",
    'delete_post': "🗑 Удалить",
    'improve_post': "✏️ Доработать",
    'cancel_post': "❌ Отменить",

    # Планировщик
    'in_30_min': "⏰ Через 30 мин",
    'in_1_hour': "🕐 Через 1 час",
    'tomorrow_9am': "📅 Завтра в 9:00",
    'choose_time': "⏰ Выбрать время",
    'distribute_auto': "🔄 Распределить",
    'set_custom_time': "⏰ Задать время",

    # Очередь
    'refresh_queue': "🔄 Обновить",
    'back_to_menu': "🔙 Назад",
    'publish_now_queue': "✅ Опубликовать сейчас",
    'change_time': "⏰ Изменить время",
    'cancel_publication': "🗑 Отменить публикацию",
    'back_to_queue': "🔙 К списку очереди",

    # Настройки
    'edit_style_prompt': "📝 Стиль и форматирование",
    'edit_group_prompt': "✂️ Обработка для группы",
    'edit_improve_prompt': "🔧 Доработка постов",
    'change_admin': "👤 Сменить админа",
    'change_group': "📢 Сменить группу",
    'show_stats': "📊 Статистика",
    'back_to_settings': "🔙 Назад к настройкам",

    # Редактирование промптов
    'view_current_prompt': "📖 Посмотреть текущий промпт",
    'edit_prompt': "✏️ Изменить промпт",
    'reset_prompt': "🔄 Сбросить на стандартный",

    # Подтверждения
    'confirm_yes': "✅ Да, передать права",
    'confirm_no': "❌ Отменить"
}

# ===============================
# 📊 НАСТРОЙКИ РАБОТЫ
# ===============================
SETTINGS = {
    'max_preview_length': 4000,  # Максимальная длина превью
    'media_caption_limit': 1020,  # Лимит для подписи к медиа
    'album_processing_delay': 2,  # Задержка обработки альбома (сек)
    'ai_request_timeout': 60,  # Таймаут AI запроса (сек)
    'ai_max_tokens': 4000,  # Максимум токенов от AI
    'ai_temperature': 0.7,  # Температура AI
    'deepseek_model': 'deepseek-chat',  # Модель DeepSeek
    'deepseek_base_url': 'https://api.deepseek.com',
    'log_level': 'INFO',  # Уровень логирования
    'log_file': 'bot.log'  # Файл логов
}

# ===============================
# 🎨 PROMPT NAMES (для UI)
# ===============================
PROMPT_NAMES = {
    'style_formatting': 'Стиль и форматирование',
    'group_processing': 'Обработка для группы',
    'post_improvement': 'Доработка постов'
}

# ===============================
# 📋 ВРЕМЕННЫЕ СЛОТЫ (для UI)
# ===============================
QUICK_SCHEDULE_OPTIONS = [
    {'text': BUTTONS['in_30_min'], 'minutes': 30},
    {'text': BUTTONS['in_1_hour'], 'minutes': 60},
    {'text': BUTTONS['tomorrow_9am'], 'tomorrow': True, 'hour': 9, 'minute': 0}
]