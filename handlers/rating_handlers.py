from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
from states.rating_states import RatingStates
from keyboardss.keyboards import get_question_navigation_keyboard, get_tags_keyboard, get_comment_keyboard
from keyboardss.pagination_kb import get_teachers_pagination_keyboard, get_search_actions_keyboard
from aiogram.enums import ParseMode

router = Router()

QUESTIONS = [
    {
        'number': 1,
        'text': '''<b>1. Ориентирование обучающихся на будущую профессиональную деятельность</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'professional_orientation'
    },
    {
        'number': 2,
        'text': '''<b>2. Эффективное использование цифровых образовательных ресурсов</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'digital_resources'
    },
    {
        'number': 3,
        'text': '''<b>3. Понятность требований, предъявляемых к обучающимся</b>

К сдаче зачетов и экзаменов, к курсовым, расчетно-графическим, лабораторным работам и т.п.

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'clear_requirements'
    },
    {
        'number': 4,
        'text': '''<b>4. Объективность и справедливость оценки учебных достижений обучающихся</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'fair_assessment'
    },
    {
        'number': 5,
        'text': '''<b>5. Индивидуальный подход к обучающимся</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'individual_approach'
    },
    {
        'number': 6,
        'text': '''<b>6. Доступность и последовательность изложения</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'clear_explanation'
    },
    {
        'number': 7,
        'text': '''<b>7. Организованность и пунктуальность</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'organization'
    },
    {
        'number': 8,
        'text': '''<b>8. Готовность оказать помощь в освоении дисциплины</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'willingness_to_help'
    },
    {
        'number': 9,
        'text': '''<b>9. Коммуникабельность (эффективное взаимодействие с обучающимися)</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'communication'
    },
    {
        'number': 10,
        'text': '''<b>10. Уважение и тактичность в отношении к обучающимся</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'respect'
    },
    {
        'number': 11,
        'text': '''<b>11. Умение создавать благоприятный социально-психологический климат</b>

Оцените как проявляется это качество у преподавателя:

• (5) Качество проявляется всегда
• (4) Качество проявляется часто  
• (3) Качество проявляется скорее редко, чем часто
• (2) Качество проявляется редко
• (1) Качество не проявляется

<b>Выберите оценку от 1 до 5:</b>''',
        'key': 'positive_climate'
    }
]

QUESTION_FLOW = [
    'professional_orientation', 'digital_resources', 'clear_requirements',
    'fair_assessment', 'individual_approach', 'clear_explanation',
    'organization', 'willingness_to_help', 'communication',
    'respect', 'positive_climate'
]


@router.message(F.text == "🎯 Оценить преподавателя")
async def start_rating(message: Message, state: FSMContext):
    teachers = db.get_all_teachers()

    if not teachers:
        await message.answer("В базе пока нет преподавателей.")
        return

    total_teachers = len(teachers)
    await message.answer(
        f"👨‍🏫 <b>Выберите преподавателя для оценки</b>\n\n"
        f"Всего преподавателей в базе: <b>{total_teachers}</b>.",
        reply_markup=get_teachers_pagination_keyboard(teachers),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingStates.choosing_teacher)


@router.callback_query(F.data.startswith("teacher_"), RatingStates.choosing_teacher)
async def choose_teacher(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора преподавателя для оценки"""
    teacher_id = int(callback.data.split("_")[1])
    teacher = db.get_teacher(teacher_id)

    if not teacher:
        await callback.answer("Преподаватель не найден")
        return

    teacher_name = db.get_teacher_full_name(teacher_id)

    survey_message = await callback.message.answer(
        f"📝 <b>Оценка преподавателя:</b> {teacher_name}\n\n"
        f"{QUESTIONS[0]['text']}",
        reply_markup=get_question_navigation_keyboard(1, len(QUESTIONS)),
        parse_mode=ParseMode.HTML
    )

    await state.update_data(
        teacher_id=teacher_id,
        teacher_name=teacher_name,
        current_question=0,
        answers={},
        survey_message_id=survey_message.message_id
    )

    await state.set_state(RatingStates.answering_professional_orientation)
    await callback.answer()


async def update_question_message(callback: CallbackQuery, state: FSMContext, question_index: int):
    """Обновляет существующее сообщение с вопросом"""
    state_data = await state.get_data()
    survey_message_id = state_data.get('survey_message_id')
    teacher_name = state_data.get('teacher_name')

    question = QUESTIONS[question_index]

    try:
        await callback.bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=survey_message_id,
            text=f"📝 <b>Оценка преподавателя:</b> {teacher_name}\n\n{question['text']}",
            reply_markup=get_question_navigation_keyboard(question['number'], len(QUESTIONS)),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Error editing message: {e}")
        new_message = await callback.message.answer(
            f"📝 <b>Оценка преподавателя:</b> {teacher_name}\n\n{question['text']}",
            reply_markup=get_question_navigation_keyboard(question['number'], len(QUESTIONS)),
            parse_mode=ParseMode.HTML
        )
        await state.update_data(survey_message_id=new_message.message_id)


QUESTION_STATES = [
    RatingStates.answering_professional_orientation,
    RatingStates.answering_digital_resources,
    RatingStates.answering_clear_requirements,
    RatingStates.answering_fair_assessment,
    RatingStates.answering_individual_approach,
    RatingStates.answering_clear_explanation,
    RatingStates.answering_organization,
    RatingStates.answering_willingness_to_help,
    RatingStates.answering_communication,
    RatingStates.answering_respect,
    RatingStates.answering_positive_climate
]

for i, state in enumerate(QUESTION_STATES):
    @router.callback_query(F.data.startswith("q_"), state)
    async def process_question_answer(callback: CallbackQuery, state: FSMContext, question_index=i):
        """Обработчик ответа на вопрос"""
        parts = callback.data.split('_')
        question_num = int(parts[1])
        score = int(parts[3])

        state_data = await state.get_data()
        answers = state_data.get('answers', {})
        current_question_index = state_data.get('current_question', 0)

        question_key = QUESTIONS[current_question_index]['key']
        answers[question_key] = score
        await state.update_data(answers=answers)

        await callback.answer(f"Оценка {score} сохранена!")

for i in range(len(QUESTIONS) - 1):
    @router.callback_query(F.data.startswith(f"next_{i + 1}"), QUESTION_STATES[i])
    async def next_question(callback: CallbackQuery, state: FSMContext, current_index=i):
        """Переход к следующему вопросу"""
        next_index = current_index + 1

        if next_index < len(QUESTIONS):
            await state.update_data(current_question=next_index)
            await update_question_message(callback, state, next_index)

            await state.set_state(QUESTION_STATES[next_index])

        await callback.answer()

for i in range(1, len(QUESTIONS)):
    @router.callback_query(F.data.startswith(f"prev_{i + 1}"), QUESTION_STATES[i])
    async def prev_question(callback: CallbackQuery, state: FSMContext, current_index=i):
        """Переход к предыдущему вопросу"""
        prev_index = current_index - 1

        if prev_index >= 0:
            await state.update_data(current_question=prev_index)
            await update_question_message(callback, state, prev_index)

            await state.set_state(QUESTION_STATES[prev_index])

        await callback.answer()


@router.callback_query(F.data == "finish_survey", RatingStates.answering_positive_climate)
async def finish_survey(callback: CallbackQuery, state: FSMContext):
    """Завершение опроса"""
    state_data = await state.get_data()
    answers = state_data.get('answers', {})
    survey_message_id = state_data.get('survey_message_id')

    if len(answers) != len(QUESTIONS):
        await callback.answer("Ответьте на все вопросы перед завершением!")
        return

    try:
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=survey_message_id
        )
    except:
        pass

    tags_message = await callback.message.answer(
        "📊 Опрос завершен! Теперь выберите теги, характеризующие преподавателя (от 3 до 10 тегов):\n\n"
        "Выберите теги:",
        reply_markup=get_tags_keyboard()
    )

    await state.update_data(tags_message_id=tags_message.message_id)
    await state.set_state(RatingStates.choosing_tags)
    await callback.answer()


@router.callback_query(F.data.startswith("tag_"), RatingStates.choosing_tags)
async def process_tag(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора тега"""
    tag = callback.data.split("_", 1)[1]

    state_data = await state.get_data()
    selected_tags = state_data.get('selected_tags', [])
    tags_message_id = state_data.get('tags_message_id')

    if tag in selected_tags:
        selected_tags.remove(tag)
    else:
        if len(selected_tags) < 10:
            selected_tags.append(tag)
        else:
            await callback.answer("Можно выбрать не более 10 тегов")
            return

    await state.update_data(selected_tags=selected_tags)

    try:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=tags_message_id,
            reply_markup=get_tags_keyboard(selected_tags)
        )
    except:
        new_message = await callback.message.answer(
            "Выберите теги:",
            reply_markup=get_tags_keyboard(selected_tags)
        )
        await state.update_data(tags_message_id=new_message.message_id)

    await callback.answer()


@router.callback_query(F.data == "finish_tags", RatingStates.choosing_tags)
async def finish_tags(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора тегов"""
    state_data = await state.get_data()
    selected_tags = state_data.get('selected_tags', [])
    tags_message_id = state_data.get('tags_message_id')

    if len(selected_tags) < 3:
        await callback.answer("Нужно выбрать минимум 3 тега")
        return

    try:
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=tags_message_id
        )
    except:
        pass

    await callback.message.answer(
        "🏷️ Теги сохранены! Теперь вы можете оставить комментарий (по желанию):\n\n"
        "Напишите ваш отзыв или нажмите кнопку чтобы пропустить:",
        reply_markup=get_comment_keyboard()
    )
    await state.set_state(RatingStates.writing_comment)
    await callback.answer()


@router.callback_query(F.data == "skip_tags", RatingStates.choosing_tags)
async def skip_tags(callback: CallbackQuery, state: FSMContext):
    """Пропуск выбора тегов"""
    await state.update_data(selected_tags=[])

    state_data = await state.get_data()
    tags_message_id = state_data.get('tags_message_id')

    try:
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=tags_message_id
        )
    except:
        pass

    await callback.message.answer(
        "Вы пропустили выбор тегов. Теперь вы можете оставить комментарий (по желанию):",
        reply_markup=get_comment_keyboard()
    )
    await state.set_state(RatingStates.writing_comment)
    await callback.answer()


@router.message(RatingStates.writing_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обработчик комментария"""
    comment = message.text

    if len(comment) > 1000:
        await message.answer("Комментарий слишком длинный (максимум 1000 символов). Сократите его:")
        return

    await save_rating(message, state, comment)


@router.callback_query(F.data == "skip_comment", RatingStates.writing_comment)
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    """Пропуск комментария"""
    await save_rating(callback.message, state, None)
    await callback.answer()


async def save_rating(message: Message, state: FSMContext, comment: str = None):
    """Сохранение оценки в БД"""
    state_data = await state.get_data()

    answers = state_data.get('answers', {})
    selected_tags = state_data.get('selected_tags', [])
    teacher_id = state_data.get('teacher_id')
    teacher_name = state_data.get('teacher_name')

    total_score = sum(answers.values())
    final_score = total_score / len(answers) if answers else 0

    db.save_rating(
        teacher_id=teacher_id,
        score=final_score,
        tags=selected_tags,
        comment=comment
    )

    result_text = f"""
✅ <b>Оценка сохранена!</b>

Преподаватель: <b>{teacher_name}</b>
Итоговая оценка: <b>{final_score:.1f}/5.0</b>

Выбранные теги: {', '.join(selected_tags) if selected_tags else 'не выбраны'}
Комментарий: {comment if comment else 'не оставлен'}
    """

    await message.answer(result_text, parse_mode=ParseMode.HTML)
    await state.clear()


@router.callback_query(F.data.startswith("page_"), RatingStates.choosing_teacher)
async def paginate_teachers(callback: CallbackQuery, state: FSMContext):
    """Обработчик пагинации в состоянии выбора преподавателя"""
    parts = callback.data.split('_')
    page = int(parts[1])
    search_query = parts[2] if len(parts) > 2 else ""

    teachers = db.get_all_teachers()

    if search_query:
        teachers = search_teachers(teachers, search_query)

    await callback.message.edit_reply_markup(
        reply_markup=get_teachers_pagination_keyboard(teachers, page, search_query=search_query)
    )
    await callback.answer()


@router.callback_query(F.data == "search_teacher", RatingStates.choosing_teacher)
async def start_search(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала поиска преподавателя"""
    await callback.message.answer(
        "🔍 <b>Поиск преподавателя</b>\n\n"
        "Введите ФИО преподавателя для поиска:\n"
        "• Можно ввести фамилию\n"
        "• Или фамилию и имя\n"
        "• Или полное ФИО",
        reply_markup=get_search_actions_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingStates.searching_teacher)
    await callback.answer()


@router.callback_query(F.data == "cancel_search", RatingStates.searching_teacher)
async def cancel_search(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены поиска"""
    teachers = db.get_all_teachers()

    await callback.message.answer(
        "👨‍🏫 <b>Выберите преподавателя для оценки</b>",
        reply_markup=get_teachers_pagination_keyboard(teachers),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingStates.choosing_teacher)
    await callback.answer()


@router.message(RatingStates.searching_teacher)
async def process_search(message: Message, state: FSMContext):
    """Обработчик ввода поискового запроса"""
    search_query = message.text.strip()

    if len(search_query) < 2:
        await message.answer("❌ Введите хотя бы 2 символа для поиска")
        return

    teachers = db.get_all_teachers()
    filtered_teachers = search_teachers(teachers, search_query)

    if not filtered_teachers:
        await message.answer(
            f"❌ Преподаватели по запросу \"<b>{search_query}</b>\" не найдены.\n"
            "Попробуйте другой запрос или отмените поиск.",
            parse_mode=ParseMode.HTML
        )
        return

    await message.answer(
        f"🔍 <b>Результаты поиска:</b> \"<b>{search_query}</b>\"\n"
        f"Найдено преподавателей: <b>{len(filtered_teachers)}</b>",
        reply_markup=get_teachers_pagination_keyboard(filtered_teachers, search_query=search_query),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingStates.choosing_teacher)


@router.callback_query(F.data == "show_all_teachers", RatingStates.choosing_teacher)
async def show_all_teachers(callback: CallbackQuery, state: FSMContext):
    """Обработчик показа всех преподавателей"""
    teachers = db.get_all_teachers()

    await callback.message.edit_text(
        f"👨‍🏫 <b>Все преподаватели</b>\n\n"
        f"Всего преподавателей: <b>{len(teachers)}</b>",
        reply_markup=get_teachers_pagination_keyboard(teachers),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


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
