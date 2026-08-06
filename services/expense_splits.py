from db import queries


async def handle_grouped_expense(transaction_id: int, participants: list[dict]) -> None:
    await queries.save_expense_participants(transaction_id, participants)


async def mark_participant_paid(
    person_name: str, amount_paid: float | None = None
) -> dict | None:
    """Находит самый свежий открытый долг человека и отмечает его возвращённым."""
    open_expense = await queries.find_open_expense_by_person(person_name)
    if open_expense is None:
        return None
    return await queries.mark_participant_paid(
        open_expense["transaction_id"], person_name, amount_paid
    )


async def get_debt_summary() -> list[dict]:
    return await queries.get_debt_summary()
