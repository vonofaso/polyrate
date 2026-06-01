from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from database import db
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

logger = logging.getLogger(__name__)
router = Router()


class ReportStates(StatesGroup):
    """Состояния для системы жалоб"""
    writing_reason = State()


def get_report_review_keyboard(review_id: int):
    """
    Клавиатура с кнопкой Пожаловаться для конкретного отзыва.
    Принимает review_id, а не teacher_id!
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🚩 Пожаловаться", callback_data=f"report_{review_id}")
    builder.button(text="🔙 Назад к списку", callback_data="back_to_list")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data.startswith("report_"))
async def report_review(callback: CallbackQuery, state: FSMContext):
    """Пользователь нажал 'Пожаловаться' на отзыв"""
    review_id = int(callback.data.split("_")[1])
    review = db.get_review_by_id(review_id)

    if not review:
        await callback.answer("Отзыв не найден")
        return

    # Проверяем, не жаловался ли уже пользователь на этот отзыв
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM reports WHERE review_id = ? AND reporter_id = ? AND status = 'pending'",
            (review_id, callback.from_user.id)
        )
        if cursor.fetchone():
            await callback.answer(
                "⚠️ Вы уже пожаловались на этот отзыв. Модератор рассмотрит вашу жалобу.",
                show_alert=True
            )
            return

    await state.update_data(report_review_id=review_id)

    await callback.message.answer(
        "📝 <b>Жалоба на отзыв</b>\n\n"
        "Пожалуйста, укажите причину жалобы одним сообщением.\n"
        "Опишите, что именно вас не устраивает в этом отзыве "
        "(спам, оскорбление, неточность и т.д.)\n\n"
        "<i>Причина должна содержать от 10 до 500 символов.</i>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(ReportStates.writing_reason)
    await callback.answer()


@router.message(ReportStates.writing_reason)
async def process_report_reason(message: Message, state: FSMContext, bot: Bot):
    """Обрабатывает причину жалобы и отправляет модераторам"""
    reason = message.text.strip()

    if len(reason) < 10 or len(reason) > 500:
        await message.answer(
            "❌ Причина должна содержать от 10 до 500 символов.\n"
            "Пожалуйста, введите причину ещё раз:"
        )
        return

    state_data = await state.get_data()
    review_id = state_data.get('report_review_id')

    if not review_id:
        await message.answer("❌ Ошибка. Сессия истекла. Начните заново.")
        await state.clear()
        return

    try:
        # Сохраняем жалобу в БД
        report_id = db.add_report(review_id, message.from_user.id, reason)

        # Получаем информацию об отзыве для уведомления
        review = db.get_review_by_id(review_id)
        teacher_name = "Неизвестный преподаватель"
        if review:
            teacher = db.get_teacher(review['teacher_id'])
            if teacher:
                teacher_name = db.get_teacher_full_name(review['teacher_id'])

        # Импортируем ADMIN_IDS напрямую
        from handlers.admin_handlers import ADMIN_IDS

        from keyboardss.admin_keyboards import get_admin_review_notification_keyboard

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🚩 <b>Новая жалоба на отзыв!</b>\n\n"
                    f"👤 <b>Жалоба #{report_id}</b>\n"
                    f"📝 <b>Отзыв #{review_id}</b>\n"
                    f"👨‍🏫 <b>Преподаватель:</b> {teacher_name}\n"
                    f"📋 <b>Причина:</b>\n{reason}\n\n"
                    f"<i>Перейдите в панель администратора для рассмотрения</i>",
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"Report notification sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        await message.answer(
            "✅ <b>Ваша жалоба отправлена на рассмотрение!</b>\n\n"
            "Спасибо за помощь в улучшении качества контента. "
            "Модератор рассмотрит вашу жалобу в ближайшее время.",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Error processing report: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке жалобы. "
            "Пожалуйста, попробуйте позже."
        )

    await state.clear()
