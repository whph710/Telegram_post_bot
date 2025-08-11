# -*- coding: utf-8 -*-
import logging
import sys
from bot import bot, dp
from handlers import router
from config import MY_ID


async def on_startup():
    """Действия при запуске бота"""
    try:
        await bot.send_message(MY_ID, "🤖 Бот запущен и готов к обработке постов!")
        logging.info("Бот успешно запущен")
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления о старте: {e}")


async def on_shutdown():
    """Действия при завершении работы бота"""
    try:
        await bot.send_message(MY_ID, "🛑 Бот завершает работу...")
        logging.info("Бот завершил работу")
    except Exception as e:
        logging.error(f"Ошибка при завершении: {e}")


if __name__ == "__main__":
    # Настройка UTF-8 для stdout в Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("bot.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

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
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)