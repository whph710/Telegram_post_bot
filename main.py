# -*- coding: utf-8 -*-
import logging
import sys
import os
from bot import bot, dp
from handlers import router
from config import MY_ID


async def on_startup():
    """Действия при запуске бота"""
    try:
        await bot.send_message(MY_ID, "Бот запущен и готов к обработке постов!")
        logging.info("Бот успешно запущен")
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления о старте: {e}")


async def on_shutdown():
    """Действия при завершении работы бота"""
    try:
        await bot.send_message(MY_ID, "Бот завершает работу...")
        logging.info("Бот завершил работу")
    except Exception as e:
        logging.error(f"Ошибка при завершении: {e}")


if __name__ == "__main__":
    # Настройка логирования с корректной кодировкой UTF-8
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            # Файловый обработчик с явным указанием UTF-8
            logging.FileHandler("bot.log", encoding='utf-8', mode='a'),
            # Консольный обработчик
            logging.StreamHandler()
        ],
        # Принудительно используем UTF-8
        encoding='utf-8',
        errors='replace'
    )

    # Отключаем избыточное логирование сторонних библиотек
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)

    # Регистрируем роутер
    dp.include_router(router)

    # Регистрируем события
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("Запускаем бота...")
        dp.run_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)