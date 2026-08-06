from db import queries


async def handle_offset_expense(transaction: dict) -> dict:
    """Регистрирует расход как открытый взаимозачёт для контрагента."""
    return await queries.save_offset(
        source_transaction_id=transaction["id"],
        counterparty_id=transaction["counterparty_id"],
        amount=transaction["amount"],
    )


async def check_open_offsets(counterparty_id: int) -> list[dict]:
    return await queries.get_open_offsets(counterparty_id)


async def apply_offsets_to_payment(offsets: list[dict], payment_transaction_id: int) -> float:
    """Помечает зачёты применёнными к платежу, возвращает суммарно применённую сумму."""
    total = sum(o["amount"] for o in offsets)
    offset_ids = [o["id"] for o in offsets]
    await queries.apply_offsets(offset_ids, payment_transaction_id)
    return total
