import re

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from services import reporting

router = Router(name="reporting")

DATE_RANGE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})$")


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    balances = await reporting.get_counterparty_balances()
    await message.answer(reporting.format_balance(balances))


@router.message(Command("debts"))
async def cmd_debts(message: Message) -> None:
    debts = await reporting.get_debt_summary()
    await message.answer(reporting.format_debts(debts))


@router.message(Command("export"))
async def cmd_export(message: Message, command: CommandObject) -> None:
    args = (command.args or "").strip()
    match = DATE_RANGE_RE.match(args)
    if not match:
        await message.answer(
            "Формат: /export ГГГГ-ММ-ДД:ГГГГ-ММ-ДД\n"
            "Например: /export 2025-08-01:2025-08-31"
        )
        return

    start_date, end_date = match.group(1), match.group(2)
    await message.answer("Готовлю файл...")

    buffer = await reporting.generate_excel(start_date, end_date)
    filename = f"export_{start_date}_{end_date}.xlsx"
    await message.answer_document(
        BufferedInputFile(buffer.read(), filename=filename)
    )
