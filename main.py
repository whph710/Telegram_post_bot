
import logging
import sys
import os
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
    # Принудительная установка кодировки UTF-8 для всей системы
    if sys.platform.startswith('win'):
        # Для Windows устанавливаем UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')

    # Настройка логирования с принудительным UTF-8
    class UTF8Formatter(logging.Formatter):
        def format(self, record):
            msg = super().format(record)
            # Обеспечиваем корректную кодировку
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8', errors='replace')
            return msg

    # Создаем форматтер
    formatter = UTF8Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Настраиваем логирование
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Убираем старые обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Файловый обработчик
    file_handler = logging.FileHandler("bot.log", encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Отключаем логирование aiogram на уровне INFO (слишком много сообщений)
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)

    # Регистрируем роутер
    dp.include_router(router)

    # Регистрируем события
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("🚀 Запускаем бота...")
        dp.run_polling(bot)
    except KeyboardInterrupt:
        logger.info("⏹️ Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)