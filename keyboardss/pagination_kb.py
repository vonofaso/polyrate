from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_teachers_pagination_keyboard(teachers, page: int = 0, page_size: int = 10, search_query: str = ""):
    """Клавиатура с пагинацией для списка преподавателей"""
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
            text=full_name,
            callback_data=f"teacher_{teacher['id']}"
        )

    total_pages = (len(teachers) + page_size - 1) // page_size

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"page_{page - 1}_{search_query}"
        ))

    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"page_{page + 1}_{search_query}"
        ))

    if pagination_buttons:
        builder.row(*pagination_buttons)

    builder.button(
        text="🔍 Поиск преподавателя",
        callback_data="search_teacher"
    )

    builder.adjust(1)
    return builder.as_markup()


def get_search_actions_keyboard():
    """Клавиатура для действий поиска"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить поиск", callback_data="cancel_search")
    return builder.as_markup()


def get_teachers_sort_keyboard(sort_by: str = "name", page: int = 0, search_query: str = ""):
    """Клавиатура для сортировки с пагинацией"""
    builder = InlineKeyboardBuilder()

    sort_options = {
        "name": "📝 По имени",
        "rating": "⭐ По рейтингу",
        "reviews": "📊 По количеству отзывов"
    }

    for key, text in sort_options.items():
        emoji = "✅" if sort_by == key else "⬜"
        builder.button(text=f"{emoji} {text}", callback_data=f"sort_{key}_{page}_{search_query}")

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(
            text="◀️ Предыдущие",
            callback_data=f"sort_{sort_by}_{page - 1}_{search_query}"
        ))

    pagination_buttons.append(InlineKeyboardButton(
        text="Следующие ▶️",
        callback_data=f"sort_{sort_by}_{page + 1}_{search_query}"
    ))

    if pagination_buttons:
        builder.row(*pagination_buttons)

    builder.button(
        text="🔍 Поиск преподавателя",
        callback_data=f"search_sort_{sort_by}_{page}"
    )

    builder.adjust(1)
    return builder.as_markup()