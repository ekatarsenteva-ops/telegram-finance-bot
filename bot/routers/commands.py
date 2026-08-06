from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from db import queries

router = Router(name="commands")

HELP_TEXT = """Команды:
/balance — баланс контрагентов
/debts — список открытых долгов
/export ГГГГ-ММ-ДД:ГГГГ-ММ-ДД — экспорт операций в Excel
/settings — настройки по умолчанию (объект, валюта)
/cancel — отменить текущий диалог

Просто напиши операцию свободным текстом, например:
"Пришло 15000 от Пети"
"Внесли аренду за август, 50 тыс"
"Пикник 9000, делим поровну на Иву, Марию, Петра"
"""


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await queries.get_or_create_user(message.from_user.id, message.from_user.username)

    await message.answer(
        "Привет! Я помогу вести учёт финансов.\n"
        "Просто отправь сообщение про операцию в свободной форме.\n\n" + HELP_TEXT
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("❌ Диалог отменён.")


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Школа", callback_data="settings_org:1"),
                InlineKeyboardButton(text="Недвижимость", callback_data="settings_org:2"),
            ]
        ]
    )
    await message.answer(
        "Выберите объект по умолчанию (будет подставляться, если не указан в тексте):",
        reply_markup=keyboard,
    )
