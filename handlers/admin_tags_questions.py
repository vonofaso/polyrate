import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db
from states.admin_states import AdminStates

logger = logging.getLogger(__name__)
router = Router()


# ==================== УПРАВЛЕНИЕ ТЕГАМИ ====================

def get_tags_management_keyboard():
    """Клавиатура управления тегами"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Просмотр тегов", callback_data="admin_view_tags")
    builder.button(text="➕ Добавить тег", callback_data="admin_add_tag")
    builder.button(text="✏️ Редактировать тег", callback_data="admin_edit_tag_select")
    builder.button(text="❌ Удалить тег", callback_data="admin_delete_tag_select")
    builder.button(text="🔙 Назад", callback_data="admin_back_main")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "admin_tags")
async def admin_tags_menu(callback: CallbackQuery, state: FSMContext):
    """Меню управления тегами"""
    await state.clear()
    await callback.message.edit_text(
        "🏷️ <b>Управление тегами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_tags_management_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.managing_tags)
    await callback.answer()


@router.callback_query(F.data == "admin_view_tags", AdminStates.managing_tags)
async def view_all_tags(callback: CallbackQuery):
    """Просмотр всех тегов"""
    tags = db.get_all_tags()

    if not tags:
        text = "📭 <b>Список тегов пуст</b>"
    else:
        text = "🏷️ <b>Список всех тегов:</b>\n\n"
        for tag in tags:
            status = "✅" if tag['is_active'] else "❌"
            text += f"{status} <b>{tag['name']}</b> (ID: {tag['id']})\n"

    text += f"\nВсего тегов: <b>{len(tags)}</b>"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_tags")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "admin_add_tag", AdminStates.managing_tags)
async def add_tag_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления тега"""
    await callback.message.edit_text(
        "➕ <b>Добавление нового тега</b>\n\n"
        "Введите название тега (одним словом или фразой):\n"
        "<i>Пример: профессионал, хороший лектор, строгий но справедливый</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_tag_name)
    await callback.answer()


@router.message(AdminStates.waiting_tag_name)
async def process_tag_name(message: Message, state: FSMContext):
    """Обработка названия нового тега"""
    tag_name = message.text.strip().lower()

    if len(tag_name) < 2 or len(tag_name) > 50:
        await message.answer(
            "❌ Название тега должно содержать от 2 до 50 символов. Попробуйте снова:",
            reply_markup=get_cancel_keyboard()
        )
        return

    tag_id = db.add_tag(tag_name)

    if tag_id == -1:
        await message.answer(
            "❌ Тег с таким названием уже существует!",
            reply_markup=get_tags_management_keyboard()
        )
    else:
        await message.answer(
            f"✅ Тег <b>\"{tag_name}\"</b> успешно добавлен! (ID: {tag_id})",
            reply_markup=get_tags_management_keyboard(),
            parse_mode=ParseMode.HTML
        )

    await state.set_state(AdminStates.managing_tags)


@router.callback_query(F.data == "admin_edit_tag_select", AdminStates.managing_tags)
async def edit_tag_select(callback: CallbackQuery):
    """Выбор тега для редактирования"""
    tags = db.get_all_tags()

    if not tags:
        await callback.answer("Нет тегов для редактирования")
        return

    builder = InlineKeyboardBuilder()
    for tag in tags:
        status = "✅" if tag['is_active'] else "❌"
        builder.button(
            text=f"{status} {tag['name']}",
            callback_data=f"admin_edit_tag_{tag['id']}"
        )
    builder.button(text="🔙 Назад", callback_data="admin_tags")
    builder.adjust(1)

    await callback.message.edit_text(
        "✏️ <b>Выберите тег для редактирования:</b>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_tag_"))
async def edit_tag_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования конкретного тега"""
    tag_id = int(callback.data.split("_")[3])
    tag = db.get_tag(tag_id)

    if not tag:
        await callback.answer("Тег не найден")
        return

    await state.update_data(edit_tag_id=tag_id)

    await callback.message.edit_text(
        f"✏️ <b>Редактирование тега</b>\n\n"
        f"Текущее название: <b>{tag['name']}</b>\n"
        f"Статус: {'✅ Активен' if tag['is_active'] else '❌ Неактивен'}\n\n"
        f"Введите новое название тега (или отправьте '-' чтобы оставить текущее):",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_tag_edit_name)
    await callback.answer()


@router.message(AdminStates.waiting_tag_edit_name)
async def process_tag_edit(message: Message, state: FSMContext):
    """Обработка нового названия тега"""
    new_name = message.text.strip()
    state_data = await state.get_data()
    tag_id = state_data.get('edit_tag_id')

    if new_name != '-':
        if len(new_name) < 2 or len(new_name) > 50:
            await message.answer("❌ Название должно быть от 2 до 50 символов. Попробуйте снова:")
            return
        success = db.update_tag(tag_id, name=new_name.lower())
        if not success:
            await message.answer(
                "❌ Тег с таким названием уже существует!",
                reply_markup=get_tags_management_keyboard()
            )
            await state.set_state(AdminStates.managing_tags)
            return

    await message.answer(
        "✅ Тег успешно обновлен!",
        reply_markup=get_tags_management_keyboard()
    )
    await state.set_state(AdminStates.managing_tags)


@router.callback_query(F.data == "admin_delete_tag_select", AdminStates.managing_tags)
async def delete_tag_select(callback: CallbackQuery):
    """Выбор тега для удаления"""
    tags = db.get_all_tags(active_only=True)

    if not tags:
        await callback.answer("Нет активных тегов для удаления")
        return

    builder = InlineKeyboardBuilder()
    for tag in tags:
        builder.button(
            text=f"❌ {tag['name']}",
            callback_data=f"admin_delete_tag_{tag['id']}"
        )
    builder.button(text="🔙 Назад", callback_data="admin_tags")
    builder.adjust(1)

    await callback.message.edit_text(
        "❌ <b>Выберите тег для удаления:</b>\n"
        "<i>Тег будет деактивирован, но не удален полностью</i>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_tag_"))
async def delete_tag_confirm(callback: CallbackQuery):
    """Подтверждение удаления тега"""
    tag_id = int(callback.data.split("_")[3])
    tag = db.get_tag(tag_id)

    if not tag:
        await callback.answer("Тег не найден")
        return

    db.delete_tag(tag_id)

    await callback.answer(f"Тег \"{tag['name']}\" деактивирован")
    await admin_tags_menu(callback, None)


def get_cancel_keyboard():
    """Клавиатура для отмены действия"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="admin_tags")
    return builder.as_markup()


# ==================== УПРАВЛЕНИЕ ВОПРОСАМИ ====================

def get_questions_management_keyboard():
    """Клавиатура управления вопросами"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Просмотр вопросов", callback_data="admin_view_questions")
    builder.button(text="➕ Добавить вопрос", callback_data="admin_add_question")
    builder.button(text="✏️ Редактировать вопрос", callback_data="admin_edit_question_select")
    builder.button(text="❌ Удалить вопрос", callback_data="admin_delete_question_select")
    builder.button(text="🔙 Назад", callback_data="admin_back_main")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "admin_questions")
async def admin_questions_menu(callback: CallbackQuery, state: FSMContext):
    """Меню управления вопросами"""
    await state.clear()
    await callback.message.edit_text(
        "❓ <b>Управление вопросами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_questions_management_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.managing_questions)
    await callback.answer()


@router.callback_query(F.data == "admin_view_questions", AdminStates.managing_questions)
async def view_all_questions(callback: CallbackQuery):
    """Просмотр всех вопросов"""
    questions = db.get_all_questions()

    if not questions:
        text = "📭 <b>Список вопросов пуст</b>"
    else:
        text = "❓ <b>Список всех вопросов:</b>\n\n"
        for q in questions:
            status = "✅" if q['is_active'] else "❌"
            text += f"{status} <b>Вопрос {q['number']}:</b> {q['title']}\n"
            text += f"   Ключ: {q['key']} (ID: {q['id']})\n\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_questions")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "admin_add_question", AdminStates.managing_questions)
async def add_question_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления вопроса - шаг 1: номер"""
    await callback.message.edit_text(
        "➕ <b>Добавление нового вопроса</b>\n\n"
        "<b>Шаг 1/4:</b> Введите номер вопроса (целое число):",
        reply_markup=get_cancel_keyboard_questions(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_question_number)
    await callback.answer()


@router.message(AdminStates.waiting_question_number)
async def process_question_number(message: Message, state: FSMContext):
    """Обработка номера вопроса"""
    try:
        number = int(message.text.strip())
        if number < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое положительное число:")
        return

    await state.update_data(question_number=number)
    await message.answer(
        "<b>Шаг 2/4:</b> Введите заголовок вопроса (краткое название):",
        reply_markup=get_cancel_keyboard_questions(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_question_title)


@router.message(AdminStates.waiting_question_title)
async def process_question_title(message: Message, state: FSMContext):
    """Обработка заголовка вопроса"""
    title = message.text.strip()

    if len(title) < 5 or len(title) > 200:
        await message.answer("❌ Заголовок должен содержать от 5 до 200 символов:")
        return

    await state.update_data(question_title=title)
    await message.answer(
        "<b>Шаг 3/4:</b> Введите описание вопроса (развернутый текст с критериями оценки):",
        reply_markup=get_cancel_keyboard_questions(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_question_description)


@router.message(AdminStates.waiting_question_description)
async def process_question_description(message: Message, state: FSMContext):
    """Обработка описания вопроса"""
    description = message.text.strip()

    if len(description) < 10 or len(description) > 1000:
        await message.answer("❌ Описание должно содержать от 10 до 1000 символов:")
        return

    await state.update_data(question_description=description)
    await message.answer(
        "<b>Шаг 4/4:</b> Введите ключ вопроса (уникальный идентификатор на английском, например: professional_orientation):",
        reply_markup=get_cancel_keyboard_questions(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_question_key)


@router.message(AdminStates.waiting_question_key)
async def process_question_key(message: Message, state: FSMContext):
    """Обработка ключа вопроса и сохранение"""
    key = message.text.strip().lower()

    if not key.replace("_", "").isalnum():
        await message.answer("❌ Ключ должен содержать только буквы, цифры и подчеркивания:")
        return

    state_data = await state.get_data()

    question_id = db.add_question(
        number=state_data['question_number'],
        title=state_data['question_title'],
        description=state_data['question_description'],
        key=key
    )

    if question_id == -1:
        await message.answer(
            "❌ Вопрос с таким ключом или номером уже существует!",
            reply_markup=get_questions_management_keyboard()
        )
    else:
        await message.answer(
            f"✅ Вопрос успешно добавлен! (ID: {question_id})",
            reply_markup=get_questions_management_keyboard()
        )

    await state.set_state(AdminStates.managing_questions)


@router.callback_query(F.data == "admin_edit_question_select", AdminStates.managing_questions)
async def edit_question_select(callback: CallbackQuery):
    """Выбор вопроса для редактирования"""
    questions = db.get_all_questions()

    if not questions:
        await callback.answer("Нет вопросов для редактирования")
        return

    builder = InlineKeyboardBuilder()
    for q in questions:
        status = "✅" if q['is_active'] else "❌"
        builder.button(
            text=f"{status} {q['number']}. {q['title'][:30]}...",
            callback_data=f"admin_edit_question_{q['id']}"
        )
    builder.button(text="🔙 Назад", callback_data="admin_questions")
    builder.adjust(1)

    await callback.message.edit_text(
        "✏️ <b>Выберите вопрос для редактирования:</b>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_question_"))
async def edit_question_start(callback: CallbackQuery):
    """Начало редактирования вопроса - выбор поля"""
    question_id = int(callback.data.split("_")[3])
    question = db.get_question(question_id)

    if not question:
        await callback.answer("Вопрос не найден")
        return

    text = f"✏️ <b>Редактирование вопроса #{question['id']}</b>\n\n"
    text += f"<b>Номер:</b> {question['number']}\n"
    text += f"<b>Заголовок:</b> {question['title']}\n"
    text += f"<b>Ключ:</b> {question['key']}\n"
    text += f"<b>Статус:</b> {'✅ Активен' if question['is_active'] else '❌ Неактивен'}\n\n"
    text += "<b>Описание:</b>\n"
    text += question['description'][:200] + "..." if len(question['description']) > 200 else question['description']
    text += "\n\n<b>Выберите поле для редактирования:</b>"

    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Заголовок", callback_data=f"admin_edit_q_field_{question_id}_title")
    builder.button(text="📄 Описание", callback_data=f"admin_edit_q_field_{question_id}_description")
    builder.button(text="🔢 Номер", callback_data=f"admin_edit_q_field_{question_id}_number")
    builder.button(text="🔑 Ключ", callback_data=f"admin_edit_q_field_{question_id}_key")
    if question['is_active']:
        builder.button(text="❌ Деактивировать", callback_data=f"admin_edit_q_field_{question_id}_deactivate")
    else:
        builder.button(text="✅ Активировать", callback_data=f"admin_edit_q_field_{question_id}_activate")
    builder.button(text="🔙 Назад", callback_data="admin_questions")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_q_field_"))
async def edit_question_field(callback: CallbackQuery, state: FSMContext):
    """Редактирование конкретного поля вопроса"""
    parts = callback.data.split("_")
    question_id = int(parts[4])
    field = parts[5]

    if field in ['deactivate', 'activate']:
        is_active = 1 if field == 'activate' else 0
        db.update_question(question_id, is_active=is_active)
        await callback.answer(f"Вопрос {'активирован' if is_active else 'деактивирован'}")
        await admin_questions_menu(callback, state)
        return

    await state.update_data(edit_question_id=question_id, edit_question_field=field)

    field_names = {
        'title': 'заголовок',
        'description': 'описание',
        'number': 'номер',
        'key': 'ключ'
    }

    await callback.message.edit_text(
        f"✏️ Введите новое значение для поля <b>\"{field_names.get(field, field)}\"</b>:",
        reply_markup=get_cancel_keyboard_questions(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(AdminStates.waiting_question_edit_value)
    await callback.answer()


@router.message(AdminStates.waiting_question_edit_value)
async def process_question_edit_value(message: Message, state: FSMContext):
    """Обработка нового значения поля вопроса"""
    state_data = await state.get_data()
    question_id = state_data.get('edit_question_id')
    field = state_data.get('edit_question_field')
    value = message.text.strip()

    if field == 'number':
        try:
            value = int(value)
        except ValueError:
            await message.answer("❌ Введите целое число:")
            return

    kwargs = {field: value}
    success = db.update_question(question_id, **kwargs)

    if success:
        await message.answer(
            "✅ Поле успешно обновлено!",
            reply_markup=get_questions_management_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при обновлении. Возможно, такой ключ или номер уже существует.",
            reply_markup=get_questions_management_keyboard()
        )

    await state.set_state(AdminStates.managing_questions)


@router.callback_query(F.data == "admin_delete_question_select", AdminStates.managing_questions)
async def delete_question_select(callback: CallbackQuery):
    """Выбор вопроса для удаления"""
    questions = db.get_all_questions(active_only=True)

    if not questions:
        await callback.answer("Нет активных вопросов для удаления")
        return

    builder = InlineKeyboardBuilder()
    for q in questions:
        builder.button(
            text=f"❌ {q['number']}. {q['title'][:30]}...",
            callback_data=f"admin_delete_question_{q['id']}"
        )
    builder.button(text="🔙 Назад", callback_data="admin_questions")
    builder.adjust(1)

    await callback.message.edit_text(
        "❌ <b>Выберите вопрос для удаления:</b>\n"
        "<i>Вопрос будет деактивирован</i>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_question_"))
async def delete_question_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления вопроса"""
    question_id = int(callback.data.split("_")[3])
    question = db.get_question(question_id)

    if not question:
        await callback.answer("Вопрос не найден")
        return

    db.delete_question(question_id)

    await callback.answer(f"Вопрос \"{question['title'][:30]}...\" деактивирован")
    await admin_questions_menu(callback, state)


def get_cancel_keyboard_questions():
    """Клавиатура для отмены при работе с вопросами"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="admin_questions")
    return builder.as_markup()