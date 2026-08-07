import io

from openpyxl import Workbook

from db import queries

TRANSACTIONS_HEADER = [
    "Дата",
    "Объект",
    "Тип",
    "Сумма",
    "Валюта",
    "Категория",
    "Контрагент",
    "Статус",
    "Кто внес",
]

TYPE_LABELS = {
    "income": "приход",
    "expense": "расход",
    "incoming_payment": "платёж",
}

STATUS_LABELS = {
    "income": "приход",
    "incoming_payment": "приход",
    "expense": "расход",
}


def format_balance(balances: list[dict]) -> str:
    if not balances:
        return "Открытых взаимозачётов нет."

    lines = ["Баланс контрагентов (открытые взаимозачёты):"]
    for row in balances:
        lines.append(
            f"{row['counterparty_name']}: {row['open_offset_amount']:g}₽ "
            f"({row['open_offset_count']} шт.)"
        )
    return "\n".join(lines)


def format_debts(debts: list[dict]) -> str:
    if not debts:
        return "Открытых долгов нет."

    lines = ["Открытые долги:"]
    for row in debts:
        lines.append(
            f"{row['person_name']}: {row['total_debt']:g}₽ "
            f"(не вернул: {row['pending_returns']} из {row['total_expenses']})"
        )
    return "\n".join(lines)


async def get_counterparty_balances() -> list[dict]:
    return await queries.get_counterparty_balances()


async def get_debt_summary() -> list[dict]:
    return await queries.get_debt_summary()


async def generate_excel(start_date: str, end_date: str) -> io.BytesIO:
    transactions = await queries.get_transactions_for_period(start_date, end_date)

    wb = Workbook()
    ws = wb.active
    ws.title = "Транзакции"
    ws.append(TRANSACTIONS_HEADER)

    group_ids = []
    for t in transactions:
        status = "взаимозачёт" if t["is_offset"] else STATUS_LABELS[t["type"]]
        ws.append(
            [
                t["date"].isoformat(),
                t["organization_name"],
                TYPE_LABELS[t["type"]],
                float(t["amount"]),
                t["currency"],
                t["category_name"] or "",
                t["counterparty_name"] or "",
                status,
                t["created_by_username"] or "",
            ]
        )
        group_ids.append(t["id"])

    participants = await queries.get_expense_participants_for_transactions(group_ids)
    if participants:
        ws2 = wb.create_sheet("Участники расходов")
        ws2.append(["ID операции", "Имя", "Сумма", "Вернул", "Дата возврата"])
        for p in participants:
            ws2.append(
                [
                    p["transaction_id"],
                    p["person_name"],
                    float(p["amount"]),
                    "да" if p["is_paid"] else "нет",
                    p["paid_date"].isoformat() if p["paid_date"] else "",
                ]
            )

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
