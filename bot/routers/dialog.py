import datetime
import logging
import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.states import TransactionFlow
from db import queries
from services import claude_parser, expense_splits, offset_manager

logger = logging.getLogger(__name__)

router = Router(name="dialog")

ORGANIZATION_NAMES = {1: "Школа языков", 2: "Недвижимость"}

CLARIFICATION_PROMPTS = {
    "organization_id": "Для какого объекта: Школа (1) или Недвижимость (2)?",
    "counterparty": "Уточните, пожалуйста, контрагента (кто внес/кто получил)? "
    "Напишите имя текстом или нажмите кнопку ниже, если контрагент не нужен.",
    "category": "Уточните категорию операции?",
    "amount": "Уточните сумму (цифра в рублях)?",
    "date": "Уточните дату операции (ГГГГ-ММ-ДД)?",
}

CLARIFICATION_ORDER = ["organization_id", "counterparty", "category", "amount", "date"]

REPAYMENT_KEYWORDS = ["вернул", "вернула", "отдал", "отдала", "оплатил", "оплатила", "вернули"]


def _sorted_clarifications(fields: list[str]) -> list[str]:
    known = [f for f in CLARIFICATION_ORDER if f in fields]
    unknown = [f for f in fields if f not in CLARIFICATION_ORDER]
    return known + unknown


async def _try_extract_repayment(text: str) -> str | None:
    lowered = text.lower()
    if not any(keyword in lowered for keyword in REPAYMENT_KEYWORDS):
        return None

    debts = await expense_splits.get_debt_summary()
    candidates = [debt["person_name"] for debt in debts]

    for name in candidates:
        if re.search(rf"(?<!\w){re.escape(name.lower())}(?!\w)", lowered):
            return name

    return claude_parser.match_repayment_name(text, candidates)


def _extract_amount(text: str) -> float | None:
    match = re.search(r"\d[\d\s]*(?:[.,]\d+)?", text)
    if not match:
        return None
    cleaned = match.group(0).replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def handle_free_text(message: Message, state: FSMContext) -> None:
    repayment_name = await _try_extract_repayment(message.text)
    if repayment_name:
        updated = await expense_splits.mark_participant_paid(repayment_name)
        if updated:
            await message.answer(f"✅ Отмечено: {repayment_name} вернул(а) долю.")
        else:
            await message.answer(
                f"Не нашёл открытого долга у «{repayment_name}». Проверьте написание имени."
            )
        return

    result = claude_parser.parse_transaction(message.text)

    if result.error:
        await message.answer(
            "Не удалось разобрать операцию. Попробуйте переформулировать или "
            "укажите сумму и контрагента явно."
        )
        return

    parsed = result.parsed.model_dump()
    await state.update_data(
        parsed=parsed,
        needs_clarification=_sorted_clarifications(parsed["needs_clarification"]),
        original_text=message.text,
        raw_response_text=result.raw_response_text,
    )
    await ask_next_clarification(message, state)


async def ask_next_clarification(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    queue = data.get("needs_clarification", [])

    if not queue:
        await proceed_after_clarification(message, state)
        return

    field = queue[0]
    remaining = queue[1:]
    await state.update_data(needs_clarification=remaining, current_field=field)
    await state.set_state(TransactionFlow.clarifying)

    if field == "organization_id":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Школа", callback_data="org_select:1"),
                    InlineKeyboardButton(text="Недвижимость", callback_data="org_select:2"),
                ]
            ]
        )
        await message.answer(CLARIFICATION_PROMPTS[field], reply_markup=keyboard)
        return

    if field == "counterparty":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Без контрагента", callback_data="counterparty_skip")]
            ]
        )
        await message.answer(CLARIFICATION_PROMPTS[field], reply_markup=keyboard)
        return

    if field == "category":
        parsed = data.get("parsed", {})
        organization_id = parsed.get("organization_id")
        if organization_id:
            categories = await queries.list_categories(organization_id)
            if categories:
                await state.update_data(category_options=categories)
                buttons = [
                    [InlineKeyboardButton(text=c["name"], callback_data=f"category_select:{c['id']}")]
                    for c in categories
                ]
                buttons.append(
                    [InlineKeyboardButton(text="✏️ Другое", callback_data="category_custom")]
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                await message.answer(CLARIFICATION_PROMPTS[field], reply_markup=keyboard)
                return

    await message.answer(CLARIFICATION_PROMPTS.get(field, f"Уточните {field}"))


@router.message(StateFilter(TransactionFlow.clarifying), F.text)
async def handle_clarification_answer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field = data.get("current_field")
    parsed = data.get("parsed", {})

    if field == "amount":
        amount = _extract_amount(message.text)
        if amount is None:
            await message.answer("Не понял сумму. Введите число, например 15000.")
            return
        parsed["amount"] = amount
    elif field == "organization_id":
        digits = re.search(r"[12]", message.text)
        if not digits:
            await message.answer("Укажите 1 (Школа) или 2 (Недвижимость).")
            return
        parsed["organization_id"] = int(digits.group(0))
    elif field == "counterparty":
        text = message.text.strip()
        if len(text.split()) > 4 or any(ch.isdigit() for ch in text):
            await message.answer(
                "Похоже, это не имя. Напишите короткое имя/название контрагента "
                "или нажмите «Без контрагента»."
            )
            return
        parsed["counterparty"] = text
    else:
        parsed[field] = message.text.strip()

    await state.update_data(parsed=parsed)
    await ask_next_clarification(message, state)


async def proceed_after_clarification(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    parsed = data["parsed"]

    if parsed["transaction_type"] == "incoming_payment" and parsed.get("counterparty"):
        counterparty = await queries.get_or_create_counterparty(parsed["counterparty"])
        open_offsets = await offset_manager.check_open_offsets(counterparty["id"])
        if open_offsets:
            total = sum(o["amount"] for o in open_offsets)
            await state.update_data(
                open_offsets=open_offsets, counterparty_id=counterparty["id"]
            )
            await state.set_state(TransactionFlow.offset_decision)
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Да", callback_data="offset_apply:yes"),
                        InlineKeyboardButton(text="❌ Нет", callback_data="offset_apply:no"),
                    ]
                ]
            )
            await message.answer(
                f"На счёте открытых взаимозачётов: {total:g}₽. Применить к этому платежу?",
                reply_markup=keyboard,
            )
            return

    await show_confirmation(message, state)


def format_confirmation(parsed: dict) -> str:
    org_name = ORGANIZATION_NAMES.get(parsed.get("organization_id"), "?")
    amount = parsed["amount"]
    date = parsed.get("date") or datetime.date.today().isoformat()

    if parsed.get("split_participants"):
        participants_str = "\n".join(
            f"  • {p['name']}: {p['amount']:g}₽" for p in parsed["split_participants"]
        )
        return (
            f"💰 Групповой расход: {amount:g}₽\n"
            f"Объект: {org_name}\n"
            f"Дата: {date}\n"
            f"Долги:\n{participants_str}"
        )

    if parsed.get("is_offset"):
        return (
            f"💸 Расход с взаимозачётом: {amount:g}₽\n"
            f"Контрагент: {parsed.get('counterparty') or '—'}\n"
            f"Зачет в: {parsed.get('category') or '—'}\n"
            f"Объект: {org_name}\n"
            f"Дата: {date}"
        )

    type_label = {
        "income": "✅ Приход",
        "expense": "💸 Расход",
        "incoming_payment": "📥 Платёж",
    }[parsed["transaction_type"]]

    return (
        f"{type_label}: {amount:g}₽\n"
        f"Контрагент: {parsed.get('counterparty') or '—'}\n"
        f"Объект: {org_name}\n"
        f"Категория: {parsed.get('category') or '—'}\n"
        f"Дата: {date}"
    )


async def show_confirmation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    parsed = data["parsed"]
    await state.set_state(TransactionFlow.confirming)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"),
            ]
        ]
    )
    await message.answer(format_confirmation(parsed), reply_markup=keyboard)
