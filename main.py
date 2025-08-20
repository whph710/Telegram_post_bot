# -*- coding: utf-8 -*-
import asyncio
import logging
import sys
import os

from bot import bot, dp
from config import ADMIN_ID, MESSAGES, SETTINGS

# Импорт всех хендлеров
from handlers import menu, post_creation, settings, scheduler

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
        await bot.send_message(ADMIN_ID, MESSAGES['bot_started'])
        logging.info("🚀 Бот успешно запущен")

    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")


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
    logging.basicConfig(
        level=getattr(logging, SETTINGS['log_level'].upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(SETTINGS['log_file'], encoding='utf-8', mode='a'),
            logging.StreamHandler()
        ]
    )

    # Настройка уровней логирования для внешних библиотек
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai._base_client").setLevel(logging.WARNING)


async def main():
    """Главная функция"""
    # Настраиваем логирование
    setup_logging()
    logger = logging.getLogger(__name__)

    # Проверяем конфигурацию
    if not ADMIN_ID:
        logger.error("❌ Не задан ADMIN_ID")
        sys.exit(1)

    # Регистрируем роутеры
    dp.include_router(menu.router)
    dp.include_router(post_creation.router)
    dp.include_router(settings.router)
    dp.include_router(scheduler.router)

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