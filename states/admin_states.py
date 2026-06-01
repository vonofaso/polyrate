from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния для административной панели"""
    choosing_action = State()

    # Управление преподавателями
    waiting_teacher_last_name = State()
    waiting_teacher_first_name = State()
    waiting_teacher_patronymic = State()
    waiting_teacher_department = State()
    waiting_teacher_position = State()
    waiting_teacher_edit_field = State()
    waiting_teacher_edit_value = State()
    waiting_teacher_delete_confirm = State()
    viewing_stats = State()

    # Модерация
    viewing_reports = State()
    reviewing_report = State()
    waiting_rejection_reason = State()

    # Поиск
    searching_teacher_edit = State()
    searching_teacher_delete = State()
    waiting_teacher_delete = State()
    confirm_delete = State()

    # Управление тегами
    managing_tags = State()
    waiting_tag_name = State()
    waiting_tag_edit_name = State()

    # Управление вопросами
    managing_questions = State()
    waiting_question_number = State()
    waiting_question_title = State()
    waiting_question_description = State()
    waiting_question_key = State()
    waiting_question_edit_field = State()
    waiting_question_edit_value = State()

    # Черный список
    managing_bad_words = State()
    waiting_bad_word_add = State()
    waiting_bad_word_remove = State()