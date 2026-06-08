import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot

from database import db
from states.admin_states import AdminStates
from keyboardss.admin_keyboards import (
    get_admin_main_keyboard, get_admin_teachers_keyboard,
    get_teachers_delete_list_keyboard, get_admin_reviews_keyboard,
    get_review_moderation_keyboard, get_cancel_keyboard,
    get_admin_search_keyboard, get_delete_confirm_keyboard,
    get_admin_review_notification_keyboard, get_stats_keyboard
)

logger = logging.getLogger(__name__)
router = Router()

# Список администраторов (ID пользователей Telegram)
ADMIN_IDS = []


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


def search_teachers(teachers, search_query: str):
    """Поиск преподавателей по ФИО"""
    if not search_query:
        return teachers

    search_lower = search_query.lower()
    results = []

    for teacher in teachers:
        full_name_variants = [
            f"{teacher['last_name']} {teacher['first_name']} {teacher['patronymic']}".lower().strip(),
            f"{teacher['last_name']} {teacher['first_name']}".lower(),
            f"{teacher['last_name']}".lower(),
            f"{teacher['first_name']} {teacher['last_name']}".lower(),
            f"{teacher['first_name']} {teacher['patronymic']}".lower(),
        ]

        for variant in full_name_variants:
            if search_lower in variant:
                results.append(teacher)
                break

    return results


# ==================== МОДЕРАЦИЯ ЖАЛОБ ====================

@router.callback_query(F.data == "admin_reports")
async def admin_reports(callback: CallbackQuery, state: FSMContext):
    """Показывает список жалоб на модерации"""
    pending_reports = db.get_pending_reports()

    if not pending_reports:
        await callback.message.edit_text(
            "📭 <b>Нет жалоб на рассмотрении</b>",
            reply_markup=get_admin_main_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    text = f"🚩 <b>Модерация жалоб</b>\n\nОжидает рассмотрения: <b>{len(pending_reports)}</b>\n\n"
    text += "<i>Выберите жалобу для рассмотрения:</i>"

    builder = InlineKeyboardBuilder()
    for report in pending_reports:
        review = db.get_review_by_id(report['review_id'])
        if review:
            teacher_name = db.get_teacher_full_name(review['teacher_id'])
            short_text = f"Жалоба #{report['id']} на {teacher_name}"
            builder.button(text=short_text, callback_data=f"admin_report_{report['id']}")

    builder.button(text="🔙 Назад", callback_data="admin_back_main")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await state.set_state(AdminStates.viewing_reports)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_report_"), AdminStates.viewing_reports)
async def view_report(callback: CallbackQuery, state: FSMContext):
    report_id = int(callback.data.split("_")[2])

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        report = cursor.fetchone()
        if report:
            review = db.get_review_by_id(report['review_id'])
            if review:
                teacher_name = db.get_teacher_full_name(review['teacher_id'])
                tags = json.loads(review['tags']) if review['tags'] else []

                text = f"🚩 <b>Жалоба #{report['id']}</b>\n\n"
                text += f"<b>На отзыв:</b> #{review['id']}\n"
                text += f"<b>Преподаватель:</b> {teacher_name}\n"
                text += f"<b>Оценка:</b> {'⭐' * int(review['score'])} {review['score']:.1f}/5.0\n"
                if tags: text += f"<b>Теги:</b> {', '.join(tags)}\n"
                if review['comment']: text += f"<b>Комментарий:</b>\n{review['comment']}\n\n"
                text += f"<b>Причина жалобы:</b>\n{report['reason']}\n\n"
                text += f"<i>От: {datetime.strptime(report['created_at'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')}</i>"

                builder = InlineKeyboardBuilder()
                builder.button(text="✅ Принять (удалить отзыв)", callback_data=f"admin_accept_report_{report_id}")
                builder.button(text="❌ Отклонить жалобу", callback_data=f"admin_reject_report_{report_id}")
                builder.button(text="🔙 Назад к списку", callback_data="admin_reports")
                builder.adjust(1)

                await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
                await callback.answer()
                return

    await callback.answer("Жалоба не найдена")


@router.callback_query(F.data.startswith("admin_accept_report_"))
async def accept_report(callback: CallbackQuery, bot: Bot):
    report_id = int(callback.data.split("_")[3])
    if db.approve_report(report_id):
        await callback.message.edit_text("✅ Жалоба принята. Отзыв удален.", reply_markup=get_admin_main_keyboard())
    else:
        await callback.answer("Ошибка при удалении")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_reject_report_"))
async def reject_report(callback: CallbackQuery):
    report_id = int(callback.data.split("_")[3])
    if db.reject_report(report_id):
        await callback.message.edit_text("❌ Жалоба отклонена. Отзыв сохранен.", reply_markup=get_admin_main_keyboard())
    else:
        await callback.answer("Ошибка при отклонении")
    await callback.answer()


# ==================== НАСТРОЙКИ (ОТЧЕТЫ) ====================
@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    current_interval = db.get_setting('report_interval')
    text = f"⚙️ <b>Настройки</b>\n\n"
    text += f"<b>Автоматические отчеты:</b> {current_interval}\n\n"
    text += "Выберите интервал отправки отчета:"

    builder = InlineKeyboardBuilder()
    for interval, label in [('daily', 'Ежедневно'), ('weekly', 'Еженедельно'), ('off', 'Отключить')]:
        prefix = '✅ ' if current_interval == interval else ''
        builder.button(text=f"{prefix}{label}", callback_data=f"set_report_{interval}")
    builder.button(text="🔙 Назад", callback_data="admin_back_main")
    builder.adjust(2, 1, 1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("set_report_"))
async def set_report_interval(callback: CallbackQuery):
    interval = callback.data.split("_")[2]
    db.set_setting('report_interval', interval)
    await callback.answer(f"Интервал изменен на {interval}")
    await admin_settings(callback)


# ==================== ЧЕРНЫЙ СПИСОК СЛОВ ====================
@router.callback_query(F.data == "admin_bad_words")
async def manage_bad_words(callback: CallbackQuery, state: FSMContext):
    words = db.get_banned_words()
    text = "🤬 <b>Запрещенные слова</b>\n\n"
    if words:
        text += ", ".join(words)
    else:
        text += "<i>Список пуст</i>"
    text += "\n\nВыберите действие:"

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить слово", callback_data="add_bad_word")
    builder.button(text="➖ Удалить слово", callback_data="remove_bad_word")
    builder.button(text="🔙 Назад", callback_data="admin_back_main")
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await state.set_state(AdminStates.managing_bad_words)


@router.callback_query(F.data == "add_bad_word", AdminStates.managing_bad_words)
async def add_bad_word_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите слово или несколько слов через запятую, которые нужно добавить:")
    await state.set_state(AdminStates.waiting_bad_word_add)


@router.message(AdminStates.waiting_bad_word_add)
async def process_add_bad_word(message: Message, state: FSMContext):
    words = message.text.split(',')
    for word in words:
        db.add_banned_word(word.strip().lower())
    await message.answer("✅ Слова добавлены!")
    await state.clear()


@router.callback_query(F.data == "remove_bad_word", AdminStates.managing_bad_words)
async def remove_bad_word_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите слово или несколько слов через запятую, которые нужно удалить из списка:")
    await state.set_state(AdminStates.waiting_bad_word_remove)


@router.message(AdminStates.waiting_bad_word_remove)
async def process_remove_bad_word(message: Message, state: FSMContext):
    words = message.text.split(',')
    for word in words:
        db.remove_banned_word(word.strip().lower())
    await message.answer("✅ Слова удалены!")
    await state.clear()


# ==================== ЭКСПОРТ ДАННЫХ ====================
@router.callback_query(F.data == "admin_export_main")
async def export_main_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Экспорт пользователей", callback_data="export_users")
    builder.button(text="👨‍🏫 Экспорт преподавателей", callback_data="export_teachers")
    builder.button(text="📝 Экспорт отзывов", callback_data="export_reviews")
    builder.button(text="🔙 Назад", callback_data="admin_back_main")
    builder.adjust(1)
    await callback.message.edit_text(
        "📤 <b>Экспорт данных</b>\n\nВыберите, что хотите экспортировать:",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("export_"))
async def export_data(callback: CallbackQuery):
    export_type = callback.data.split("_")[1]

    if export_type == "users":
        data = db.export_users_to_csv()
        filename = "users_export.csv"
    elif export_type == "teachers":
        data = db.export_teachers_to_csv()
        filename = "teachers_export.csv"
    elif export_type == "reviews":
        data = db.export_reviews_to_csv()
        filename = "reviews_export.csv"
    else:
        return

    doc = BufferedInputFile(data.encode('utf-8'), filename=filename)
    await callback.message.answer_document(doc, caption=f"Экспорт {filename}")
    await callback.answer()


async def notify_admins_new_review(bot: Bot, review_id: int, teacher_name: str, score: float):
    """Отправляет уведомление всем админам о новом отзыве"""

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📝 <b>Новый отзыв опубликован!</b>\n\n"
                f"👨‍🏫 Преподаватель: {teacher_name}\n"
                f"⭐ Оценка: {score:.1f}/5.0\n"
                f"🆔 ID отзыва: {review_id}\n\n"
                f"<i>Отзыв автоматически опубликован</i>",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

# ==================== АВТОМАТИЧЕСКИЕ ОТЧЕТЫ ====================
async def scheduled_reports(bot: Bot):
    """Фоновая задача для отправки отчетов"""
    while True:
        now = datetime.now()
        interval = db.get_setting('report_interval')

        if interval == 'daily':
            next_run = now.replace(hour=9, minute=0, second=0) + timedelta(days=1)
        elif interval == 'weekly':
            days_ahead = 0 - now.weekday()  # Понедельник
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now.replace(hour=9, minute=0, second=0) + timedelta(days=days_ahead)
        else:  # off
            next_run = now + timedelta(hours=1)

        sleep_seconds = (next_run - now).total_seconds()
        await asyncio.sleep(sleep_seconds)

        if interval != 'off':
            stats = db.get_statistics()
            report = f"📊 <b>Автоматический отчет</b>\n\n"
            report += f"📝 Всего отзывов: {stats['total_ratings']}\n"
            report += f"⭐ Средний балл: {stats['avg_score']}/5.0\n"
            report += f"🚩 Жалоб на рассмотрении: {stats['pending_reports']}\n\n"
            report += "🏆 <b>Топ-5 преподавателей:</b>\n"
            for i, teacher in enumerate(stats['top_by_rating'][:5], 1):
                report += f"{i}. {teacher['name']} - {teacher['avg_score']}⭐ ({teacher['count']})\n"

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, report, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Failed to send report to {admin_id}: {e}")

@router.message(F.text == "👨‍💼 Панель администратора")
async def admin_panel_button(message: Message, state: FSMContext):
    """Обработчик кнопки панели администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return

    await state.clear()

    await message.answer(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    """Вход в админ-панель по команде"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return

    await state.clear()

    await message.answer(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "admin_back_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню админки"""
    await state.clear()
    await callback.message.edit_text(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "admin_exit")
async def exit_admin(callback: CallbackQuery, state: FSMContext):
    """Выход из админ-панели"""
    await state.clear()
    await callback.message.delete()
    await callback.answer("👋 Выход из панели администратора")


@router.callback_query(F.data == "admin_cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await callback.message.edit_text(
        "👨‍💼 <b>Панель администратора</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


# ==================== УПРАВЛЕНИЕ ПРЕПОДАВАТЕЛЯМИ ====================

@router.callback_query(F.data == "admin_teachers")
async def admin_teachers(callback: CallbackQuery, state: FSMContext):
    """Управление преподавателями"""
    await callback.message.edit_text(
        "👨‍🏫 <b>Управление преподавателями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_teachers_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.choosing_action)
    await callback.answer()


# ==================== ДОБАВЛЕНИЕ ПРЕПОДАВАТЕЛЯ ====================

@router.callback_query(F.data == "admin_add_teacher", AdminStates.choosing_action)
async def add_teacher_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления преподавателя"""
    await callback.message.edit_text(
        "➕ <b>Добавление нового преподавателя</b>\n\n"
        "Введите <b>фамилию</b> преподавателя:",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_teacher_last_name)
    await callback.answer()


@router.message(AdminStates.waiting_teacher_last_name)
async def process_teacher_last_name(message: Message, state: FSMContext):
    """Обработка фамилии преподавателя"""
    last_name = message.text.strip()

    if len(last_name) < 2 or len(last_name) > 50:
        await message.answer(
            "❌ Фамилия должна содержать от 2 до 50 символов. Попробуйте снова:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(last_name=last_name)

    await message.answer(
        "Введите <b>имя</b> преподавателя:",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_teacher_first_name)


@router.message(AdminStates.waiting_teacher_first_name)
async def process_teacher_first_name(message: Message, state: FSMContext):
    """Обработка имени преподавателя"""
    first_name = message.text.strip()

    if len(first_name) < 2 or len(first_name) > 50:
        await message.answer(
            "❌ Имя должно содержать от 2 до 50 символов. Попробуйте снова:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(first_name=first_name)

    await message.answer(
        "Введите <b>отчество</b> преподавателя (или отправьте '-' если нет отчества):",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_teacher_patronymic)


@router.message(AdminStates.waiting_teacher_patronymic)
async def process_teacher_patronymic(message: Message, state: FSMContext):
    """Обработка отчества преподавателя"""
    patronymic = message.text.strip()

    if patronymic == '-':
        patronymic = None
    elif len(patronymic) > 50:
        await message.answer(
            "❌ Отчество слишком длинное (макс. 50 символов). Попробуйте снова:",
            reply_markup=get_cancel_keyboard()
        )
        return

    data = await state.get_data()

    try:
        teacher_id = db.add_teacher(
            data['last_name'],
            data['first_name'],
            patronymic
        )

        teacher_name = db.get_teacher_full_name(teacher_id)

        await message.answer(
            f"✅ <b>Преподаватель успешно добавлен!</b>\n\n"
            f"ID: {teacher_id}\n"
            f"ФИО: {teacher_name}",
            reply_markup=get_admin_teachers_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await state.set_state(AdminStates.choosing_action)
    except Exception as e:
        logger.error(f"Error adding teacher: {e}")
        await message.answer(
            "❌ Произошла ошибка при добавлении преподавателя.",
            reply_markup=get_admin_teachers_keyboard()
        )
        await state.set_state(AdminStates.choosing_action)


# ==================== УДАЛЕНИЕ ПРЕПОДАВАТЕЛЯ ====================

@router.callback_query(F.data == "admin_delete_teacher", AdminStates.choosing_action)
async def delete_teacher_list(callback: CallbackQuery, state: FSMContext):
    """Показывает список преподавателей для удаления"""
    teachers = db.get_all_teachers()

    if not teachers:
        await callback.message.edit_text(
            "📭 В базе нет преподавателей.",
            reply_markup=get_admin_teachers_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
        return

    await state.update_data(all_teachers=teachers, current_page=0)

    await callback.message.edit_text(
        "❌ <b>Удаление преподавателя</b>\n\n"
        "Выберите преподавателя из списка или воспользуйтесь поиском:\n"
        "<i>Внимание! Это действие удалит преподавателя и все его оценки.</i>",
        reply_markup=get_teachers_delete_list_keyboard(teachers),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_teacher_delete)
    await callback.answer()


@router.callback_query(F.data == "admin_delete_search", AdminStates.waiting_teacher_delete)
async def delete_teacher_search_start(callback: CallbackQuery, state: FSMContext):
    """Начинает поиск преподавателя для удаления"""
    await callback.message.edit_text(
        "🔍 <b>Поиск преподавателя для удаления</b>\n\n"
        "Введите ФИО преподавателя для поиска:\n"
        "• Можно ввести фамилию\n"
        "• Или фамилию и имя\n"
        "• Или полное ФИО\n\n"
        "<i>Внимание! Это действие удалит преподавателя и все его оценки.</i>",
        reply_markup=get_admin_search_keyboard("delete"),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.searching_teacher_delete)
    await callback.answer()


@router.message(AdminStates.searching_teacher_delete)
async def process_delete_teacher_search(message: Message, state: FSMContext):
    """Обрабатывает поисковый запрос для удаления"""
    search_query = message.text.strip()

    if len(search_query) < 2:
        await message.answer(
            "❌ Введите хотя бы 2 символа для поиска",
            reply_markup=get_admin_search_keyboard("delete")
        )
        return

    teachers = db.get_all_teachers()
    filtered_teachers = search_teachers(teachers, search_query)

    if not filtered_teachers:
        await message.answer(
            f"❌ Преподаватели по запросу \"<b>{search_query}</b>\" не найдены.\n"
            "Попробуйте другой запрос или отмените поиск.",
            reply_markup=get_admin_search_keyboard("delete"),
            parse_mode=ParseMode.HTML
        )
        return

    await state.update_data(search_results=filtered_teachers, search_query=search_query)

    await message.answer(
        f"🔍 <b>Результаты поиска:</b> \"<b>{search_query}</b>\"\n"
        f"Найдено преподавателей: <b>{len(filtered_teachers)}</b>\n\n"
        f"<i>Внимание! Это действие удалит преподавателя и все его оценки.</i>",
        reply_markup=get_teachers_delete_list_keyboard(filtered_teachers, page=0, search_mode=True),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "admin_delete_search_cancel", AdminStates.searching_teacher_delete)
async def cancel_delete_teacher_search(callback: CallbackQuery, state: FSMContext):
    """Отменяет поиск при удалении и возвращает к полному списку"""
    teachers = db.get_all_teachers()

    await callback.message.edit_text(
        "❌ <b>Удаление преподавателя</b>\n\n"
        "Выберите преподавателя из списка или воспользуйтесь поиском:\n"
        "<i>Внимание! Это действие удалит преподавателя и все его оценки.</i>",
        reply_markup=get_teachers_delete_list_keyboard(teachers),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_teacher_delete)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_page_"))
async def delete_teacher_page(callback: CallbackQuery, state: FSMContext):
    """Пагинация списка преподавателей для удаления"""
    parts = callback.data.split("_")
    page = int(parts[3])
    search_mode = len(parts) > 4 and parts[4] == "search"

    state_data = await state.get_data()

    if search_mode:
        teachers = state_data.get('search_results', db.get_all_teachers())
        search_query = state_data.get('search_query', '')
    else:
        teachers = db.get_all_teachers()
        search_query = ''

    await callback.message.edit_reply_markup(
        reply_markup=get_teachers_delete_list_keyboard(
            teachers,
            page=page,
            search_mode=search_mode,
            search_query=search_query
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_select_"), AdminStates.waiting_teacher_delete)
@router.callback_query(F.data.startswith("admin_delete_select_"), AdminStates.searching_teacher_delete)
async def select_teacher_to_delete(callback: CallbackQuery, state: FSMContext):
    """Выбор преподавателя для удаления (подтверждение)"""
    teacher_id = int(callback.data.split("_")[3])
    teacher = db.get_teacher(teacher_id)

    if not teacher:
        await callback.answer("Преподаватель не найден")
        return

    teacher_name = db.get_teacher_full_name(teacher_id)
    ratings = db.get_teacher_ratings(teacher_id, moderated_only=False)
    ratings_count = len(ratings)

    await state.update_data(
        deleting_teacher_id=teacher_id,
        deleting_teacher_name=teacher_name
    )

    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"<b>Преподаватель:</b> {teacher_name}\n"
        f"<b>Количество оценок:</b> {ratings_count}\n\n"
        f"Вы уверены, что хотите удалить этого преподавателя?\n"
        f"<b>Это действие нельзя отменить!</b>",
        reply_markup=get_delete_confirm_keyboard(teacher_id),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.confirm_delete)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_delete_"), AdminStates.confirm_delete)
async def process_delete_teacher(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения удаления"""
    teacher_id = int(callback.data.split("_")[3])
    state_data = await state.get_data()
    teacher_name = state_data.get('deleting_teacher_name', 'Неизвестный преподаватель')

    try:
        success = db.delete_teacher(teacher_id)

        if success:
            await callback.message.edit_text(
                f"✅ <b>Преподаватель удален</b>\n\n"
                f"{teacher_name} и все связанные оценки удалены из базы.",
                reply_markup=get_admin_teachers_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.edit_text(
                "❌ Не удалось удалить преподавателя.",
                reply_markup=get_admin_teachers_keyboard(),
                parse_mode=ParseMode.HTML
            )
        await state.set_state(AdminStates.choosing_action)
    except Exception as e:
        logger.error(f"Error deleting teacher: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при удалении преподавателя.",
            reply_markup=get_admin_teachers_keyboard()
        )
        await state.set_state(AdminStates.choosing_action)

    await callback.answer()


@router.callback_query(F.data == "admin_delete_cancel", AdminStates.confirm_delete)
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    """Отмена удаления - возврат к списку"""
    teachers = db.get_all_teachers()

    await callback.message.edit_text(
        "❌ <b>Удаление преподавателя</b>\n\n"
        "Выберите преподавателя из списка или воспользуйтесь поиском:",
        reply_markup=get_teachers_delete_list_keyboard(teachers),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_teacher_delete)
    await callback.answer()


@router.callback_query(F.data == "admin_back_teachers")
async def back_to_teachers(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню управления преподавателями"""
    await callback.message.edit_text(
        "👨‍🏫 <b>Управление преподавателями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_teachers_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.choosing_action)
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def show_statistics(callback: CallbackQuery, state: FSMContext):
    """Показывает статистику и аналитику"""
    stats = db.get_statistics()

    # Формируем текст статистики
    text = "📊 <b>Статистика и аналитика</b>\n\n"

    text += "<b>📝 Общая статистика по оценкам:</b>\n"
    text += f"• Всего опубликованных оценок: <b>{stats['total_ratings']}</b>\n"
    text += f"• Средний балл по всем преподавателям: <b>{stats['avg_score']}/5.0</b>\n"
    text += f"• Оценок на модерации: <b>{stats['pending_ratings']}</b>\n"
    text += f"• Отклоненных оценок: <b>{stats['rejected_ratings']}</b>\n\n"

    # Топ-10 по среднему рейтингу
    text += "<b>🏆 Топ-10 преподавателей по среднему рейтингу:</b>\n"
    if stats['top_by_rating']:
        for i, teacher in enumerate(stats['top_by_rating'], 1):
            text += f"{i}. {teacher['name']} - {teacher['avg_score']}⭐ ({teacher['count']} оценок)\n"
    else:
        text += "Нет данных\n"
    text += "\n"

    # Топ-10 по количеству оценок
    text += "<b>📊 Топ-10 преподавателей по количеству оценок:</b>\n"
    if stats['top_by_count']:
        for i, teacher in enumerate(stats['top_by_count'], 1):
            text += f"{i}. {teacher['name']} - {teacher['count']} оценок (ср. {teacher['avg_score']}⭐)\n"
    else:
        text += "Нет данных\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_stats_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.viewing_stats)
    await callback.answer()


