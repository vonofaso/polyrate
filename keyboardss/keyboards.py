from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🎯 Оценить преподавателя")],
        [KeyboardButton(text="📊 Посмотреть рейтинги")],
        [KeyboardButton(text="ℹ️ О боте")],
        [KeyboardButton(text="📖 Помощь")]
    ]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_teachers_keyboard(teachers):
    """Клавиатура для выбора преподавателя"""
    builder = InlineKeyboardBuilder()

    for teacher in teachers:
        full_name = f"{teacher['last_name']} {teacher['first_name']}"
        if teacher['patronymic']:
            full_name += f" {teacher['patronymic']}"

        builder.button(
            text=full_name,
            callback_data=f"teacher_{teacher['id']}"
        )

    builder.adjust(1)
    return builder.as_markup()


def get_rating_keyboard():
    """Клавиатура для оценки от 1 до 5"""
    builder = InlineKeyboardBuilder()

    for i in range(1, 6):
        builder.button(text=str(i), callback_data=f"score_{i}")

    builder.adjust(5)
    return builder.as_markup()


def get_question_navigation_keyboard(question_number: int, total_questions: int):
    """Клавиатура для навигации по вопросам"""
    builder = InlineKeyboardBuilder()

    for i in range(1, 6):
        builder.button(text=str(i), callback_data=f"q_{question_number}_score_{i}")

    navigation_buttons = []
    if question_number > 1:
        navigation_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"prev_{question_number}"
        ))

    if question_number < total_questions:
        navigation_buttons.append(InlineKeyboardButton(
            text="Далее ▶️",
            callback_data=f"next_{question_number}"
        ))
    else:
        navigation_buttons.append(InlineKeyboardButton(
            text="📊 Завершить опрос",
            callback_data="finish_survey"
        ))

    builder.adjust(5)
    if navigation_buttons:
        builder.row(*navigation_buttons)

    return builder.as_markup()


def get_tags_keyboard(selected_tags=None):
    """Клавиатура для выбора тегов"""
    if selected_tags is None:
        selected_tags = []

    tags = [
        "принципиальный", "высокомерный", "любит глумиться", "торгуется на оценку",
        "лоялен к девушкам", "добрый", "придирчивый", "щедрый на оценки",
        "отзывчивый", "взаимодействует онлайн", "гордый", "требовательный",
        "уважает учащихся", "кричит", "нудный", "грубый", "интересный материал",
        "хорошее чувство юмора", "бдительный на экзамене", "надменный",
        "отмечает", "скромный", "неадекватный", "ставит автомат", "строгий",
        "сложный экзамен", "адекватный", "странный", "входит в положение",
        "конфликтный", "проверяет лекции", "злопамятный", "разрешает телефоны",
        "общительный", "хорошие презентации", "эмоциональный", "пропускает занятия",
        "опытный", "работал по профессии", "мотивирует", "помогает на экзамене",
        "вежливый", "лояльный", "лоялен к парням", "хороший научный руководитель",
        "одержим наукой"
    ]

    builder = InlineKeyboardBuilder()

    for tag in tags:
        is_selected = tag in selected_tags
        emoji = "✅" if is_selected else "⬜"
        builder.button(text=f"{emoji} {tag}", callback_data=f"tag_{tag}")

    builder.button(text="🚫 Пропустить теги", callback_data="skip_tags")
    if len(selected_tags) >= 3:
        builder.button(text="📤 Продолжить", callback_data="finish_tags")

    builder.adjust(2)
    return builder.as_markup()


def get_comment_keyboard():
    """Клавиатура для комментария"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Пропустить комментарий", callback_data="skip_comment")
    return builder.as_markup()


def get_teacher_details_keyboard(teacher_id: int, current_page: int = 0, total_pages: int = 1):
    """Клавиатура для детальной информации о преподавателе с пагинацией"""
    builder = InlineKeyboardBuilder()

    pagination_buttons = []
    if current_page > 0:
        pagination_buttons.append(InlineKeyboardButton(
            text="◀️ Предыдущий",
            callback_data=f"teacher_detail_{teacher_id}_{current_page - 1}"
        ))

    if current_page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="Следующий ▶️",
            callback_data=f"teacher_detail_{teacher_id}_{current_page + 1}"
        ))

    if pagination_buttons:
        builder.row(*pagination_buttons)

    builder.button(
        text="📋 Назад к списку",
        callback_data="back_to_ratings_list"
    )

    builder.adjust(1)
    return builder.as_markup()