import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

from handlers.start import router as start_router
from handlers.rating_handlers import router as rating_router
from handlers.view_ratings import router as view_ratings_router
from handlers.admin_handlers import router as admin_router, scheduled_reports
from handlers.report_handlers import router as report_router
from handlers.admin_tags_questions import router as admin_tags_questions_router
from middleware.logging_middleware import LoggingMiddleware

# Настройка логирования с выводом в консоль и файл
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler('bot.log', encoding='utf-8')  # Запись в файл
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Запуск основного цикла бота...")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем все роутеры с логированием
    routers = [
        ("start", start_router),
        ("rating", rating_router),
        ("view_ratings", view_ratings_router),
        ("admin", admin_router),
        ("reports", report_router),
        ("tags_questions", admin_tags_questions_router)
    ]

    for name, router in routers:
        dp.include_router(router)
        logger.info(f"✅ Роутер '{name}' подключен")
    dp.update.middleware(LoggingMiddleware())
    logger.info("🔧 Middleware логирования подключен")

    logger.info(f"📊 Всего подключено роутеров: {len(routers)}")

    # Запускаем фоновую задачу для отчетов
    logger.info("⏰ Запуск фоновой задачи для автоматических отчетов...")
    asyncio.create_task(scheduled_reports(bot))
    logger.info("✅ Фоновая задача отчетов запущена")

    # Информация о боте
    logger.info("=" * 60)
    logger.info("🤖 Бот готов к работе!")
    logger.info(f"📝 Старт polling...")
    logger.info("=" * 60)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"💥 Критическая ошибка при работе бота: {e}", exc_info=True)
    finally:
        logger.info("👋 Бот остановлен")
        await bot.session.close()
        logger.info("🔒 Сессия бота закрыта")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.critical(f"💥 Необработанная ошибка: {e}", exc_info=True)