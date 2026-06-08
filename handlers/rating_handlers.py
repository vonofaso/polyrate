import re
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
from states.rating_states import RatingStates
from keyboardss.keyboards import get_question_navigation_keyboard, get_tags_keyboard, get_comment_keyboard
from keyboardss.pagination_kb import get_teachers_pagination_keyboard, get_search_actions_keyboard
from aiogram.enums import ParseMode

router = Router()

def get_questions_from_db():
    """Получает список вопросов из базы данных"""
    questions_db = db.get_all_questions(active_only=True)

    questions = []
    question_flow = []

    for q in questions_db:
        question = {
            'number': q['number'],
            'text': f"<b>{q['number']}. {q['title']}</b>\n\n{q['description']}\n\n<b>Выберите оценку от 1 до 5:</b>",
            'key': q['key']
        }
        questions.append(question)
        question_flow.append(q['key'])

    return questions, question_flow


QUESTIONS, QUESTION_FLOW = get_questions_from_db()

def contains_bad_words(text: str) -> bool:
    if not text:
        return False
    words = db.get_banned_words()
    pattern = r'\b(' + '|'.join(re.escape(word) for word in words) + r')\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


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
    user_id = callback.from_user.id
    teacher = db.get_teacher(teacher_id)

    if not teacher:
        await callback.answer("Преподаватель не найден")
        return

    # Проверка на повторный отзыв
    if db.has_user_rated_teacher(user_id, teacher_id):
        await callback.answer("❌ Вы уже оставляли отзыв этому преподавателю!", show_alert=True)
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
        next_index = current_index + 1
        if next_index < len(QUESTIONS):
            await state.update_data(current_question=next_index)
            await update_question_message(callback, state, next_index)
            await state.set_state(QUESTION_STATES[next_index])
        await callback.answer()

for i in range(1, len(QUESTIONS)):
    @router.callback_query(F.data.startswith(f"prev_{i + 1}"), QUESTION_STATES[i])
    async def prev_question(callback: CallbackQuery, state: FSMContext, current_index=i):
        prev_index = current_index - 1
        if prev_index >= 0:
            await state.update_data(current_question=prev_index)
            await update_question_message(callback, state, prev_index)
            await state.set_state(QUESTION_STATES[prev_index])
        await callback.answer()


@router.callback_query(F.data == "finish_survey", RatingStates.answering_positive_climate)
async def finish_survey(callback: CallbackQuery, state: FSMContext):
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
    except Exception:
        new_message = await callback.message.answer(
            "Выберите теги:",
            reply_markup=get_tags_keyboard(selected_tags)
        )
        await state.update_data(tags_message_id=new_message.message_id)

    await callback.answer()


@router.callback_query(F.data == "finish_tags", RatingStates.choosing_tags)
async def finish_tags(callback: CallbackQuery, state: FSMContext):
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
    except Exception:
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
    await state.update_data(selected_tags=[])
    state_data = await state.get_data()
    tags_message_id = state_data.get('tags_message_id')
    try:
        await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=tags_message_id)
    except Exception:
        pass
    await callback.message.answer(
        "Вы пропустили выбор тегов. Теперь вы можете оставить комментарий (по желанию):",
        reply_markup=get_comment_keyboard()
    )
    await state.set_state(RatingStates.writing_comment)
    await callback.answer()


@router.message(RatingStates.writing_comment)
async def process_comment(message: Message, state: FSMContext):
    comment = message.text

    if len(comment) > 1000:
        await message.answer("Комментарий слишком длинный (максимум 1000 символов). Сократите его:")
        return

    if contains_bad_words(comment):
        await message.answer(
            "❌ Ваш комментарий содержит недопустимую лексику. Пожалуйста, перепишите его, соблюдая правила вежливости.",
            reply_markup=get_comment_keyboard()
        )
        return

    bot = message.bot
    await save_rating(message, state, bot, comment)


@router.callback_query(F.data == "skip_comment", RatingStates.writing_comment)
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    bot = callback.bot
    await save_rating(callback.message, state, bot, None)
    await callback.answer()


async def save_rating(message: Message, state: FSMContext, bot: Bot, comment: str = None):
    state_data = await state.get_data()
    answers = state_data.get('answers', {})
    selected_tags = state_data.get('selected_tags', [])
    teacher_id = state_data.get('teacher_id')
    teacher_name = state_data.get('teacher_name')
    user_id = message.chat.id

    total_score = sum(answers.values())
    final_score = total_score / len(answers) if answers else 0

    # Сохраняем отзыв с user_id
    review_id = db.save_rating(
        user_id=user_id,
        teacher_id=teacher_id,
        score=final_score,
        tags=selected_tags,
        comment=comment
    )

    # Отправляем уведомление админам
    from handlers.admin_handlers import notify_admins_new_review
    await notify_admins_new_review(bot, review_id, teacher_name, final_score)

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
    await callback.message.answer(
        "🔍 <b>Поиск преподавателя</b>\n\nВведите ФИО преподавателя для поиска:\n• Можно ввести фамилию\n• Или фамилию и имя\n• Или полное ФИО",
        reply_markup=get_search_actions_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingStates.searching_teacher)
    await callback.answer()

@router.callback_query(F.data == "cancel_search", RatingStates.searching_teacher)
async def cancel_search(callback: CallbackQuery, state: FSMContext):
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
    search_query = message.text.strip()
    if len(search_query) < 2:
        await message.answer("❌ Введите хотя бы 2 символа для поиска")
        return
    teachers = db.get_all_teachers()
    filtered_teachers = search_teachers(teachers, search_query)
    if not filtered_teachers:
        await message.answer(f"❌ Преподаватели по запросу \"<b>{search_query}</b>\" не найдены.\nПопробуйте другой запрос или отмените поиск.", parse_mode=ParseMode.HTML)
        return
    await message.answer(
        f"🔍 <b>Результаты поиска:</b> \"<b>{search_query}</b>\"\nНайдено преподавателей: <b>{len(filtered_teachers)}</b>",
        reply_markup=get_teachers_pagination_keyboard(filtered_teachers, search_query=search_query),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingStates.choosing_teacher)

@router.callback_query(F.data == "show_all_teachers", RatingStates.choosing_teacher)
async def show_all_teachers(callback: CallbackQuery, state: FSMContext):
    teachers = db.get_all_teachers()
    await callback.message.edit_text(
        f"👨‍🏫 <b>Все преподаватели</b>\n\nВсего преподавателей: <b>{len(teachers)}</b>",
        reply_markup=get_teachers_pagination_keyboard(teachers),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

def search_teachers(teachers, search_query: str):
    if not search_query: return teachers
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
