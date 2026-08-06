import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.routers.dialog import ask_next_clarification, show_confirmation
from bot.states import TransactionFlow
from db import queries
from services import expense_splits, offset_manager

router = Router(name="callbacks")

ORGANIZATION_NAMES = {1: "Школа языков", 2: "Недвижимость"}


@router.callback_query(F.data.startswith("settings_org:"))
async def on_settings_org(callback: CallbackQuery) -> None:
    org_id = int(callback.data.split(":")[1])
    await queries.update_user_defaults(callback.from_user.id, org_id, None)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await callback.message.answer(
        f"Объект по умолчанию: {ORGANIZATION_NAMES[org_id]}."
    )


@router.callback_query(TransactionFlow.clarifying, F.data.startswith("org_select:"))
async def on_org_select(callback: CallbackQuery, state: FSMContext) -> None:
    org_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    parsed = data["parsed"]
    parsed["organization_id"] = org_id
    await state.update_data(parsed=parsed)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await ask_next_clarification(callback.message, state)


@router.callback_query(TransactionFlow.clarifying, F.data.startswith("category_select:"))
async def on_category_select(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    options = data.get("category_options", [])
    match = next((c for c in options if c["id"] == category_id), None)
    parsed = data["parsed"]
    parsed["category"] = match["name"] if match else None
    await state.update_data(parsed=parsed)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await ask_next_clarification(callback.message, state)


@router.callback_query(TransactionFlow.clarifying, F.data == "category_custom")
async def on_category_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await callback.message.answer("Введите название категории:")


@router.callback_query(TransactionFlow.offset_decision, F.data.startswith("offset_apply:"))
async def on_offset_apply(callback: CallbackQuery, state: FSMContext) -> None:
    decision = callback.data.split(":")[1]
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()

    data = await state.get_data()
    parsed = data["parsed"]

    if decision == "yes":
        open_offsets = data["open_offsets"]
        total = sum(o["amount"] for o in open_offsets)
        parsed["amount"] = max(parsed["amount"] - total, 0)
        await state.update_data(parsed=parsed, offsets_to_apply=open_offsets)
        await callback.message.answer(f"Зачёт на {total:g}₽ будет применён к платежу.")
    else:
        await state.update_data(offsets_to_apply=None)

    await show_confirmation(callback.message, state)


@router.callback_query(TransactionFlow.confirming, F.data == "confirm")
async def on_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()

    data = await state.get_data()
    parsed = data["parsed"]

    user = await queries.get_or_create_user(
        callback.from_user.id, callback.from_user.username
    )

    counterparty = None
    if parsed.get("counterparty"):
        counterparty = await queries.get_or_create_counterparty(parsed["counterparty"])

    category = None
    if parsed.get("category") and parsed.get("organization_id"):
        category_type = "expense" if parsed["transaction_type"] == "expense" else "income"
        category = await queries.get_or_create_category(
            parsed["organization_id"], parsed["category"], category_type
        )

    date = parsed.get("date") or datetime.date.today().isoformat()
    currency = parsed.get("currency") or "RUB"

    raw_log = {
        "input_text": data.get("original_text"),
        "ai_response": data.get("raw_response_text"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }

    transaction = await queries.save_transaction(
        user_id=user["id"],
        organization_id=parsed["organization_id"],
        type_=parsed["transaction_type"],
        amount=parsed["amount"],
        currency=currency,
        date=date,
        category_id=category["id"] if category else None,
        counterparty_id=counterparty["id"] if counterparty else None,
        is_offset=bool(parsed.get("is_offset")),
        raw_ai_log=raw_log,
    )

    if parsed.get("is_offset") and counterparty:
        await offset_manager.handle_offset_expense(
            {
                "id": transaction["id"],
                "counterparty_id": counterparty["id"],
                "amount": transaction["amount"],
            }
        )

    if parsed.get("split_participants"):
        await expense_splits.handle_grouped_expense(
            transaction["id"], parsed["split_participants"]
        )

    offsets_to_apply = data.get("offsets_to_apply")
    if offsets_to_apply:
        await offset_manager.apply_offsets_to_payment(offsets_to_apply, transaction["id"])

    await state.clear()
    await callback.message.answer("✅ Операция записана!")


@router.callback_query(TransactionFlow.confirming, F.data == "cancel")
async def on_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await state.clear()
    await callback.message.answer("❌ Отменено")
