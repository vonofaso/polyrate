from aiogram import Router, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from database import db
from keyboardss.keyboards import get_main_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    db.add_user(
        id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    await message.answer(
        "👋 Добро пожаловать в бот для оценки преподавателей Московского политеха!\n\n"
        "Здесь вы можете:\n"
        "• Оценить преподавателей по различным критериям\n"
        "• Оставить отзывы с тегами\n"
        "• Посмотреть рейтинги других преподавателей\n\n"
        "Выберите действие в меню ниже:",
        reply_markup=get_main_keyboard()
        , parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await show_help(message)


@router.message(F.text == "📖 Помощь")
async def button_help(message: Message):
    await show_help(message)


async def show_help(message: Message):
    help_text = """
📖 <b>Помощь по боту</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Помощь

<b>Как оценить преподавателя:</b>
1. Нажмите "🎯 Оценить преподавателя"
2. Выберите преподавателя из списка
3. Ответьте на вопросы опросника
4. Выберите от 3 до 10 тегов, характеризующих преподавателя (по желанию)
5. Оставьте комментарий (по желанию)

<b>Просмотр рейтингов:</b>
• Нажмите "📊 Посмотреть рейтинги"
• Выберите преподавателя для просмотра оценок
    """
    await message.answer(help_text, parse_mode=ParseMode.HTML)


@router.message(F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    about_text = """
🤖 <b>О боте</b>

Этот бот создан для сбора обратной связи о преподавателях Московского политеха.

<b>Возможности:</b>
• Анонимная оценка преподавателей
• Детальный опросник по разным критериям
• Система тегов для характеристики преподавателей
• Просмотр агрегированных рейтингов

Все оценки собираются анонимно и используются для улучшения образовательного процесса.
    """
    await message.answer(about_text, parse_mode=ParseMode.HTML)


@router.message(F.text == "🔙 Главное меню")
async def back_to_main(message: Message):
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard()
    )
