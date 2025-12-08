from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db
from aiogram.enums import ParseMode
import json

router = Router()


class RatingViewStates(StatesGroup):
    viewing_list = State()
    searching = State()
    viewing_teacher = State()


def calculate_teacher_stats(teacher):
    """Рассчитывает статистику преподавателя"""
    ratings = db.get_teacher_ratings(teacher['id'])
    stats = db.get_teacher_stats(teacher['id'])

    if stats['rating_count'] == 0:
        return {
            'rating_count': 0,
            'avg_score': 0,
            'popular_tags': []
        }

    all_tags = []
    for rating in ratings:
        tags = json.loads(rating['tags']) if rating['tags'] else []
        all_tags.extend(tags)

    tag_freq = {}
    for tag in all_tags:
        tag_freq[tag] = tag_freq.get(tag, 0) + 1

    popular_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        'rating_count': stats['rating_count'],
        'avg_score': round(stats['avg_score'], 1) if stats['avg_score'] else 0,
        'popular_tags': [tag for tag, count in popular_tags]
    }


def get_teachers_list_keyboard(teachers, page: int = 0, page_size: int = 10, sort_by: str = "name"):
    """Клавиатура для списка преподавателей"""
    builder = InlineKeyboardBuilder()

    start_idx = page * page_size
    end_idx = start_idx + page_size
    paginated_teachers = teachers[start_idx:end_idx]

    for teacher in paginated_teachers:
        teacher_full_name = db.get_teacher_full_name(teacher['id'])

        builder.button(
            text=teacher_full_name,
            callback_data=f"view_teacher_{teacher['id']}"
        )

    total_pages = (len(teachers) + page_size - 1) // page_size

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"list_page_{page - 1}_{sort_by}"
        ))

    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"list_page_{page + 1}_{sort_by}"
        ))

    if pagination_buttons:
        builder.row(*pagination_buttons)

    sort_buttons = [
        InlineKeyboardButton(
            text="⭐ По рейтингу" if sort_by != "rating" else "✅ По рейтингу",
            callback_data="sort_rating"
        ),
        InlineKeyboardButton(
            text="📊 По кол-ву оценок" if sort_by != "reviews" else "✅ По кол-ву оценок",
            callback_data="sort_reviews"
        ),
        InlineKeyboardButton(
            text="📝 По имени" if sort_by != "name" else "✅ По имени",
            callback_data="sort_name"
        )
    ]
    builder.row(*sort_buttons)

    builder.button(
        text="🔍 Поиск преподавателя",
        callback_data="start_search"
    )

    builder.adjust(1)
    return builder.as_markup()


def get_search_keyboard():
    """Клавиатура для поиска"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить поиск", callback_data="cancel_search")
    return builder.as_markup()


def get_teacher_details_keyboard(teacher_id: int, current_page: int, total_pages: int):
    """Клавиатура для детальной информации о преподавателе"""
    builder = InlineKeyboardBuilder()

    pagination_buttons = []
    if current_page > 0:
        pagination_buttons.append(InlineKeyboardButton(
            text="◀️ Предыдущий",
            callback_data=f"view_teacher_page_{teacher_id}_{current_page - 1}"
        ))

    if current_page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(
            text="Следующий ▶️",
            callback_data=f"view_teacher_page_{teacher_id}_{current_page + 1}"
        ))

    if pagination_buttons:
        builder.row(*pagination_buttons)

    builder.button(
        text="📋 Назад к списку",
        callback_data="back_to_list"
    )

    builder.adjust(1)
    return builder.as_markup()


def format_teachers_list(teachers, page: int, page_size: int = 10, sort_by: str = "name"):
    """Форматирует список преподавателей"""
    start_idx = page * page_size
    end_idx = start_idx + page_size
    paginated_teachers = teachers[start_idx:end_idx]

    sort_text = {
        "name": "по имени",
        "rating": "по рейтингу",
        "reviews": "по количеству оценок"
    }.get(sort_by, "по имени")

    message_text = f"<b>📊 Рейтинги преподавателей (сортировка: {sort_text})</b>\n\n"

    for i, teacher in enumerate(paginated_teachers, start_idx + 1):
        teacher_full_name = db.get_teacher_full_name(teacher['id'])

        if teacher['rating_count'] == 0:
            rating_info = "⏳ Нет оценок"
        else:
            stars = "⭐" * int(teacher['avg_score'])
            rating_info = f"{stars} {teacher['avg_score']}/5.0 ({teacher['rating_count']} оценок)"

        message_text += f"<b>{i}. {teacher_full_name}</b>\n"
        message_text += f"   {rating_info}\n"

        if teacher['popular_tags']:
            message_text += f"   🏷️ {', '.join(teacher['popular_tags'][:3])}\n"

        message_text += "\n"

    total_pages = (len(teachers) + page_size - 1) // page_size
    message_text += f"<i>Страница {page + 1} из {total_pages}</i>\n\n"
    message_text += "<i>💡 Нажмите на имя преподавателя для просмотра детальной информации</i>"

    return message_text


@router.message(F.text == "📊 Посмотреть рейтинги")
async def show_ratings(message: Message, state: FSMContext):
    """Показывает список преподавателей"""
    teachers = db.get_all_teachers()
    teachers_with_stats = []

    for teacher in teachers:
        stats = calculate_teacher_stats(teacher)
        teachers_with_stats.append({
            'id': teacher['id'],
            **stats
        })

    sorted_teachers = sorted(teachers_with_stats, key=lambda x: db.get_teacher_full_name(x['id']).lower())

    await state.update_data(
        all_teachers=teachers_with_stats,
        sorted_teachers=sorted_teachers,
        current_page=0,
        sort_by="name"
    )

    await message.answer(
        format_teachers_list(sorted_teachers, 0, sort_by="name"),
        reply_markup=get_teachers_list_keyboard(sorted_teachers, 0, sort_by="name"),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingViewStates.viewing_list)


@router.callback_query(F.data.startswith("list_page_"), RatingViewStates.viewing_list)
async def paginate_list(callback: CallbackQuery, state: FSMContext):
    """Пагинация списка преподавателей"""
    parts = callback.data.split("_")
    page = int(parts[2])
    sort_by = parts[3] if len(parts) > 3 else "name"

    state_data = await state.get_data()
    sorted_teachers = state_data.get(f'sorted_teachers_{sort_by}') or state_data.get('sorted_teachers', [])

    await callback.message.edit_text(
        format_teachers_list(sorted_teachers, page, sort_by=sort_by),
        reply_markup=get_teachers_list_keyboard(sorted_teachers, page, sort_by=sort_by),
        parse_mode=ParseMode.HTML
    )
    await state.update_data(current_page=page)
    await callback.answer()


@router.callback_query(F.data.startswith("sort_"), RatingViewStates.viewing_list)
async def change_sort_order(callback: CallbackQuery, state: FSMContext):
    """Изменяет порядок сортировки"""
    sort_by = callback.data.split("_")[1]

    state_data = await state.get_data()
    all_teachers = state_data.get('all_teachers', [])

    if sort_by == "rating":
        sorted_teachers = sorted(all_teachers, key=lambda x: (x['avg_score'], x['rating_count']), reverse=True)
    elif sort_by == "reviews":
        sorted_teachers = sorted(all_teachers, key=lambda x: (x['rating_count'], x['avg_score']), reverse=True)
    elif sort_by == "name":
        sorted_teachers = sorted(all_teachers, key=lambda x: db.get_teacher_full_name(x['id']).lower())
    else:
        sorted_teachers = all_teachers

    await state.update_data(
        **{f'sorted_teachers_{sort_by}': sorted_teachers},
        current_page=0,
        sort_by=sort_by
    )

    await callback.message.edit_text(
        format_teachers_list(sorted_teachers, 0, sort_by=sort_by),
        reply_markup=get_teachers_list_keyboard(sorted_teachers, 0, sort_by=sort_by),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "start_search", RatingViewStates.viewing_list)
async def start_search(callback: CallbackQuery, state: FSMContext):
    """Начинает поиск преподавателя"""
    await callback.message.answer(
        "🔍 <b>Поиск преподавателя</b>\n\n"
        "Введите ФИО преподавателя для поиска:\n"
        "• Можно ввести фамилию\n"
        "• Или фамилию и имя\n"
        "• Или полное ФИО",
        reply_markup=get_search_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingViewStates.searching)
    await callback.answer()


@router.callback_query(F.data == "cancel_search", RatingViewStates.searching)
async def cancel_search(callback: CallbackQuery, state: FSMContext):
    """Отменяет поиск"""
    state_data = await state.get_data()
    sort_by = state_data.get('sort_by', 'name')
    sorted_teachers = state_data.get(f'sorted_teachers_{sort_by}') or state_data.get('sorted_teachers', [])
    current_page = state_data.get('current_page', 0)

    await callback.message.edit_text(
        format_teachers_list(sorted_teachers, current_page, sort_by=sort_by),
        reply_markup=get_teachers_list_keyboard(sorted_teachers, current_page, sort_by=sort_by),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingViewStates.viewing_list)
    await callback.answer()


@router.message(RatingViewStates.searching)
async def process_search(message: Message, state: FSMContext):
    """Обрабатывает поисковый запрос"""
    search_query = message.text.strip()

    if len(search_query) < 2:
        await message.answer("❌ Введите хотя бы 2 символа для поиска")
        return

    teachers = db.get_all_teachers()
    found_teachers = []

    for teacher in teachers:
        teacher_full_name = db.get_teacher_full_name(teacher['id'])

        if (search_query.lower() in teacher_full_name.lower() or
                search_query.lower() in f"{teacher['last_name']} {teacher['first_name']}".lower() or
                search_query.lower() in teacher['last_name'].lower()):
            stats = calculate_teacher_stats(teacher)
            found_teachers.append({
                'id': teacher['id'],
                **stats
            })

    if not found_teachers:
        await message.answer(
            f"❌ Преподаватели по запросу \"<b>{search_query}</b>\" не найдены.",
            parse_mode=ParseMode.HTML
        )
        return

    sorted_found_teachers = sorted(found_teachers, key=lambda x: db.get_teacher_full_name(x['id']).lower())

    await state.update_data(
        search_results=sorted_found_teachers,
        search_page=0
    )

    await message.answer(
        f"🔍 <b>Результаты поиска:</b> \"<b>{search_query}</b>\"\n"
        f"Найдено преподавателей: <b>{len(found_teachers)}</b>\n\n" +
        format_teachers_list(sorted_found_teachers, 0, sort_by="name"),
        reply_markup=get_teachers_list_keyboard(sorted_found_teachers, 0, sort_by="name"),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingViewStates.viewing_list)


@router.callback_query(F.data.startswith("view_teacher_"), RatingViewStates.viewing_list)
async def select_teacher(callback: CallbackQuery, state: FSMContext):
    """Выбор преподавателя для просмотра детальной информации"""
    teacher_id = int(callback.data.split("_")[2])
    await show_teacher_details(callback, teacher_id, 0)
    await state.set_state(RatingViewStates.viewing_teacher)
    await callback.answer()


@router.callback_query(F.data.startswith("view_teacher_page_"), RatingViewStates.viewing_teacher)
async def paginate_teacher_details(callback: CallbackQuery, state: FSMContext):
    """Пагинация детальной информации о преподавателе"""
    parts = callback.data.split('_')
    teacher_id = int(parts[3])
    page = int(parts[4])

    await show_teacher_details(callback, teacher_id, page)
    await callback.answer()


async def show_teacher_details(callback: CallbackQuery, teacher_id: int, page: int):
    """Показывает детальную информацию о преподавателе"""
    teacher = db.get_teacher(teacher_id)

    if not teacher:
        await callback.answer("Преподаватель не найден")
        return

    teacher_name = db.get_teacher_full_name(teacher_id)
    ratings = db.get_teacher_ratings(teacher_id)

    total_pages = 1 + len(ratings)

    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0

    if page == 0:
        await show_general_info(callback, teacher, teacher_name, ratings, page, total_pages)
    else:
        await show_review_page(callback, teacher, teacher_name, ratings, page, total_pages)


async def show_general_info(callback: CallbackQuery, teacher, teacher_name: str, ratings: list, page: int,
                            total_pages: int):
    """Показывает общую информацию о преподавателе"""
    stats = calculate_teacher_stats(teacher)

    general_text = f"<b>📊 Общая информация</b>\n\n"
    general_text += f"<b>Преподаватель:</b> {teacher_name}\n\n"

    if stats['rating_count'] == 0:
        general_text += "⏳ <b>Нет оценок</b>\n"
        general_text += "Этот преподаватель еще не был оценен.\n"
    else:
        stars = "⭐" * int(stats['avg_score'])
        general_text += f"<b>Рейтинг:</b> {stars} {stats['avg_score']}/5.0\n"
        general_text += f"<b>Количество оценок:</b> {stats['rating_count']}\n\n"

        score_distribution = {}
        for rating in ratings:
            score = int(rating['score'])
            score_distribution[score] = score_distribution.get(score, 0) + 1

        general_text += "<b>Распределение оценок:</b>\n"
        for score in sorted(score_distribution.keys(), reverse=True):
            count = score_distribution[score]
            percentage = (count / len(ratings)) * 100
            general_text += f"  {score}⭐ - {count} шт. ({percentage:.1f}%)\n"

        general_text += f"\n<b>Популярные теги:</b>\n"
        if stats['popular_tags']:
            for tag in stats['popular_tags']:
                general_text += f"  • {tag}\n"
        else:
            general_text += "  нет тегов\n"

    general_text += f"\n<i>Страница 1 из {total_pages}</i>\n"
    general_text += "<i>Используйте кнопки ниже для просмотра отзывов</i>"

    await callback.message.edit_text(
        general_text,
        reply_markup=get_teacher_details_keyboard(teacher['id'], page, total_pages),
        parse_mode=ParseMode.HTML
    )


async def show_review_page(callback: CallbackQuery, teacher, teacher_name: str, ratings: list, page: int,
                           total_pages: int):
    """Показывает страницу с отзывом"""
    review_index = page - 1

    if review_index >= len(ratings):
        review_index = len(ratings) - 1

    review = ratings[review_index]

    review_text = f"<b>📝 Отзыв {page} из {total_pages - 1}</b>\n\n"
    review_text += f"<b>Преподаватель:</b> {teacher_name}\n"
    rounded_score = round(review['score'], 1)
    review_text += f"<b>Оценка:</b> {'⭐' * int(rounded_score)} {rounded_score}/5.0\n\n"

    tags = json.loads(review['tags']) if review['tags'] else []
    if tags:
        review_text += f"<b>Теги:</b> {', '.join(tags)}\n\n"

    if review['comment']:
        review_text += f"<b>💬 Комментарий:</b>\n{review['comment']}\n\n"
    else:
        review_text += "<b>💬 Комментарий:</b> не указан\n\n"

    created_date = review['created_at']
    if isinstance(created_date, str):
        try:
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
                try:
                    date_obj = datetime.strptime(created_date, fmt)
                    date_obj = date_obj + timedelta(hours=3)
                    formatted_date = date_obj.strftime('%d.%m.%Y %H:%M')
                    break
                except:
                    continue
            else:
                formatted_date = created_date[:16]
        except:
            formatted_date = created_date[:10]
    else:
        formatted_date = date_obj.strftime('%d.%m.%Y %H:%M')

    review_text += f"<i>📅 Опубликовано: {formatted_date}</i>"

    await callback.message.edit_text(
        review_text,
        reply_markup=get_teacher_details_keyboard(teacher['id'], page, total_pages),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "back_to_list", RatingViewStates.viewing_teacher)
async def back_to_list(callback: CallbackQuery, state: FSMContext):
    """Возврат к списку преподавателей"""
    state_data = await state.get_data()
    sort_by = state_data.get('sort_by', 'name')
    sorted_teachers = state_data.get(f'sorted_teachers_{sort_by}') or state_data.get('sorted_teachers', [])
    current_page = state_data.get('current_page', 0)

    await callback.message.edit_text(
        format_teachers_list(sorted_teachers, current_page, sort_by=sort_by),
        reply_markup=get_teachers_list_keyboard(sorted_teachers, current_page, sort_by=sort_by),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(RatingViewStates.viewing_list)
    await callback.answer()
