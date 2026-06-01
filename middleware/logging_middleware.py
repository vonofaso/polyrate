import logging
import time
from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        # Логируем входящее обновление
        if event.message:
            user_id = event.message.from_user.id if event.message.from_user else "Unknown"
            text = event.message.text if event.message.text else "[не текст]"
            logger.info(f"📨 Сообщение от user_id={user_id}: {text[:50]}...")

        elif event.callback_query:
            user_id = event.callback_query.from_user.id
            data_text = event.callback_query.data
            logger.info(f"🔘 Callback от user_id={user_id}: {data_text}")

        # Засекаем время обработки
        start_time = time.time()

        # Выполняем обработчик
        result = await handler(event, data)

        # Логируем время выполнения
        elapsed_time = time.time() - start_time
        logger.debug(f"⏱️ Обработка заняла {elapsed_time:.3f} сек")

        return result