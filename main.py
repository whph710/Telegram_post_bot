# -*- coding: utf-8 -*-
import asyncio
import logging
import sys
import os

from bot import bot, dp
from config import ADMIN_ID, MESSAGES, SETTINGS, validate_config, get_config_summary

# Импорт всех хендлеров
from handlers import menu, post_creation, settings
from handlers import scheduler

# Импорт сервисов
from services.scheduler_service import SchedulerService
from services.ai_processor import ai_processor

# Инициализируем планировщик
scheduler_service = None


async def create_prompt_files():
    """Создает файлы промптов если их нет"""
    from config import PROMPT_PATHS

    # Создаем директорию prompts если её нет
    prompts_dir = "prompts"
    if not os.path.exists(prompts_dir):
        os.makedirs(prompts_dir)
        logging.info(f"Создана директория {prompts_dir}")

    # Создаем файлы с стандартными промптами
    for prompt_type, file_path in PROMPT_PATHS.items():
        if not os.path.exists(file_path):
            default_prompt = ai_processor._get_default_prompt(prompt_type)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(default_prompt)
                logging.info(f"Создан файл промпта: {file_path}")
            except Exception as e:
                logging.error(f"Ошибка создания файла {file_path}: {e}")


async def on_startup():
    """Действия при запуске бота"""
    global scheduler_service

    try:
        # Проверяем конфигурацию
        is_valid, errors = validate_config()
        if not is_valid:
            logging.error("Ошибки конфигурации:")
            for error in errors:
                logging.error(f"  - {error}")

            print("\n❌ КРИТИЧЕСКИЕ ОШИБКИ КОНФИГУРАЦИИ:")
            for error in errors:
                print(f"  • {error}")

            print("\n📝 Создайте .env файл со следующими параметрами:")
            print("API_TOKEN=ваш_токен_бота")
            print("MY_ID=ваш_телеграм_id")
            print("GROUP_ID=id_группы_для_постов")
            print("DEEPSEEK=ваш_deepseek_api_key")
            sys.exit(1)

        # Создаем файлы промптов если нужно
        await create_prompt_files()

        # Проверяем подключение к AI
        ai_connected = await ai_processor.validate_connection()
        if ai_connected:
            logging.info("✅ Подключение к AI сервису проверено")
        else:
            logging.warning("⚠️ Проблемы с подключением к AI сервису")

        # Запускаем планировщик
        scheduler_service = SchedulerService(bot)
        await scheduler_service.start()

        # Уведомляем админа о запуске
        try:
            startup_message = f"{MESSAGES['bot_started']}\n\n{get_config_summary()}"
            await bot.send_message(ADMIN_ID, startup_message, parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Не удалось отправить стартовое сообщение админу: {e}")

        logging.info("🚀 Бот успешно запущен")

    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)


async def on_shutdown():
    """Действия при завершении работы бота"""
    global scheduler_service

    try:
        # Останавливаем планировщик
        if scheduler_service:
            await scheduler_service.stop()

        # Уведомляем админа о завершении
        try:
            await bot.send_message(ADMIN_ID, MESSAGES['bot_stopping'])
        except:
            pass  # Игнорируем ошибки при завершении

        logging.info("🛑 Бот завершил работу")

    except Exception as e:
        logging.error(f"Ошибка при завершении работы бота: {e}")


def setup_logging():
    """Настройка логирования"""
    # Создаем форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, SETTINGS['log_level'].upper()))

    # Очищаем существующие хендлеры
    root_logger.handlers.clear()

    # Файловый хендлер с ротацией
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            SETTINGS['log_file'],
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Ошибка создания файлового логгера: {e}")

    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Настройка уровней логирования для внешних библиотек
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai._base_client").setLevel(logging.WARNING)


def check_python_version():
    """Проверяет версию Python"""
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)


def check_dependencies():
    """Проверяет установку зависимостей"""
    required_packages = ['aiogram', 'openai', 'python-dotenv', 'httpx']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("❌ Отсутствуют необходимые пакеты:")
        for package in missing_packages:
            print(f"  • {package}")
        print("\n💡 Установите их командой:")
        print("pip install -r requirements.txt")
        sys.exit(1)


async def main():
    """Главная функция"""
    print("🚀 Запуск Telegram бота...")

    # Базовые проверки
    check_python_version()
    check_dependencies()

    # Настраиваем логирование
    setup_logging()
    logger = logging.getLogger(__name__)

    # Проверяем основные настройки
    if not ADMIN_ID:
        logger.error("❌ Не задан ADMIN_ID")
        sys.exit(1)

    # Регистрируем события
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("🚀 Запускаем бота...")
        await dp.start_polling(bot, skip_updates=True)

    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)