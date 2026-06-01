from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db


def get_admin_main_keyboard():
    """Главная клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()

    builder = InlineKeyboardBuilder()
    builder.button(text="👨‍🏫 Управление преподавателями", callback_data="admin_teachers")
    builder.button(text="🏷️ Управление тегами", callback_data="admin_tags")
    builder.button(text="❓ Управление вопросами", callback_data="admin_questions")
    builder.button(text="🚩 Модерация жалоб", callback_data="admin_reports")
    builder.button(text="📤 Экспорт данных", callback_data="admin_export_main")
    builder.button(text="🤬 Черный список слов", callback_data="admin_bad_words")
    builder.button(text="⚙️ Настройки", callback_data="admin_settings")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="🔙 Выход", callback_data="admin_exit")
    builder.adjust(1)

    builder.adjust(1)
    return builder.as_markup()


def get_stats_keyboard():
    """Клавиатура для страницы статистики"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_back_main")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_teachers_keyboard():
    """Клавиатура управления преподавателями"""
    builder = InlineKeyboardBuilder()

    builder.button(text="➕ Добавить преподавателя", callback_data="admin_add_teacher")
    builder.button(text="❌ Удалить преподавателя", callback_data="admin_delete_teacher")
    builder.button(text="🔙 Назад", callback_data="admin_back_main")

    builder.adjust(1)
    return builder.as_markup()


def get_teachers_edit_list_keyboard(page: int = 0, page_size: int = 5):
    """Клавиатура со списком преподавателей для редактирования"""
    builder = InlineKeyboardBuilder()

    teachers = db.get_all_teachers()
    start_idx = page * page_size
    end_idx = start_idx + page_size
    paginated_teachers = teachers[start_idx:end_idx]

    for teacher in paginated_teachers:
        full_name = db.get_teacher_full_name(teacher['id'])
        if len(full_name) > 30:
            full_name = full_name[:27] + "..."

        builder.button(
            text=full_name,
            callback_data=f"admin_edit_select_{teacher['id']}"
        )

    # Пагинация
    total_pages = (len(teachers) + page_size - 1) // page_size
    pagination_buttons = []

    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"admin_edit_page_{page - 1}"
        ))

    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"admin_edit_page_{page + 1}"
        ))

    if pagination_buttons:
        builder.row(*pagination_buttons)

    builder.button(text="🔙 Назад", callback_data="admin_back_teachers")
    builder.adjust(1)
    return builder.as_markup()


def get_teacher_edit_actions_keyboard(teacher_id: int):
    """Клавиатура действий для редактирования конкретного преподавателя"""
    builder = InlineKeyboardBuilder()

    fields = [
        ("Фамилия", "last_name"),
        ("Имя", "first_name"),
        ("Отчество", "patronymic"),
    ]

    for label, field in fields:
        builder.button(
            text=f"✏️ {label}",
            callback_data=f"admin_edit_field_{teacher_id}_{field}"
        )

    builder.button(text="🔙 Назад", callback_data="admin_list_teachers")
    builder.adjust(2)
    return builder.as_markup()


def get_admin_reviews_keyboard(page: int = 0, page_size: int = 5):
    """Клавиатура для модерации отзывов"""
    builder = InlineKeyboardBuilder()

    pending_reviews = db.get_pending_reviews()
    start_idx = page * page_size
    end_idx = start_idx + page_size
    paginated_reviews = pending_reviews[start_idx:end_idx]

    for review in paginated_reviews:
        teacher = db.get_teacher(review['teacher_id'])
        teacher_name = db.get_teacher_full_name(review['teacher_id']) if teacher else "Неизвестный преподаватель"

        short_name = teacher_name[:20] + "..." if len(teacher_name) > 20 else teacher_name
        review_date = review['created_at'][:10] if review['created_at'] else "?"

        builder.button(
            text=f"{short_name} - {review['score']:.1f}⭐ ({review_date})",
            callback_data=f"admin_review_{review['id']}"
        )

    # Пагинация
    total_pages = (len(pending_reviews) + page_size - 1) // page_size
    pagination_buttons = []

    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"admin_reviews_page_{page - 1}"
        ))

    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"admin_reviews_page_{page + 1}"
        ))

    if pagination_buttons:
        builder.row(*pagination_buttons)

    builder.button(text="🔙 Назад", callback_data="admin_back_main")
    builder.adjust(1)
    return builder.as_markup()


def get_review_moderation_keyboard(review_id: int):
    """Клавиатура для модерации конкретного отзыва"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Опубликовать", callback_data=f"admin_approve_{review_id}")
    builder.button(text="❌ Отклонить", callback_data=f"admin_reject_{review_id}")
    builder.button(text="🔙 Назад", callback_data="admin_reviews")

    builder.adjust(2)
    return builder.as_markup()


def get_cancel_keyboard():
    """Клавиатура для отмены действия"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="admin_cancel")
    return builder.as_markup()



def get_admin_search_keyboard(action: str = "delete"):
    """Клавиатура для поиска в админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить поиск", callback_data=f"admin_{action}_search_cancel")
    return builder.as_markup()


def get_teachers_delete_list_keyboard(teachers, page: int = 0, page_size: int = 5,
                                      search_mode: bool = False, search_query: str = ""):
    """Клавиатура со списком преподавателей для удаления"""
    builder = InlineKeyboardBuilder()

    start_idx = page * page_size
    end_idx = start_idx + page_size
    paginated_teachers = teachers[start_idx:end_idx]

    for teacher in paginated_teachers:
        full_name = f"{teacher['last_name']} {teacher['first_name']}"
        if teacher['patronymic']:
            full_name += f" {teacher['patronymic']}"

        if len(full_name) > 30:
            full_name = full_name[:27] + "..."

        builder.button(
            text=f"{full_name}",
            callback_data=f"admin_delete_select_{teacher['id']}"
        )

    # Пагинация
    total_pages = (len(teachers) + page_size - 1) // page_size
    pagination_buttons = []

    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"admin_delete_page_{page - 1}{'_search' if search_mode else ''}"
        ))

    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"admin_delete_page_{page + 1}{'_search' if search_mode else ''}"
        ))

    if pagination_buttons:
        builder.row(*pagination_buttons)

    # Кнопки действий
    builder.button(text="🔍 Поиск преподавателя", callback_data="admin_delete_search")
    builder.button(text="🔙 Назад", callback_data="admin_back_teachers")

    builder.adjust(1)
    return builder.as_markup()


def get_delete_confirm_keyboard(teacher_id: int):
    """Клавиатура для подтверждения удаления"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"admin_confirm_delete_{teacher_id}")
    builder.button(text="❌ Нет, отмена", callback_data="admin_delete_cancel")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_review_notification_keyboard(review_id: int):
    """Клавиатура для уведомления о новом отзыве"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Перейти к модерации", callback_data=f"admin_review_{review_id}")
    builder.adjust(1)
    return builder.as_markup()



