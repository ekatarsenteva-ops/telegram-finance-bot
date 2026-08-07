import json

from psycopg.rows import dict_row

from db.connection import pool


async def get_or_create_user(telegram_id: int, username: str | None) -> dict:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO users (telegram_id, username)
                VALUES (%s, %s)
                ON CONFLICT (telegram_id) DO UPDATE SET telegram_id = EXCLUDED.telegram_id
                RETURNING *
                """,
                (telegram_id, username),
            )
            row = await cur.fetchone()
            await conn.commit()
            return row


async def update_user_defaults(
    telegram_id: int, organization_id: int | None, currency: str | None
) -> None:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE users
                SET default_organization_id = COALESCE(%s, default_organization_id),
                    default_currency = COALESCE(%s, default_currency)
                WHERE telegram_id = %s
                """,
                (organization_id, currency, telegram_id),
            )
        await conn.commit()


async def list_organizations() -> list[dict]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT * FROM organizations ORDER BY id")
            return await cur.fetchall()


async def list_categories(organization_id: int) -> list[dict]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT * FROM categories WHERE organization_id = %s ORDER BY name",
                (organization_id,),
            )
            return await cur.fetchall()


async def get_or_create_category(organization_id: int, name: str, type_: str) -> dict:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT * FROM categories WHERE organization_id = %s AND lower(name) = lower(%s)",
                (organization_id, name),
            )
            row = await cur.fetchone()
            if row:
                return row

            await cur.execute(
                """
                INSERT INTO categories (organization_id, name, type)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (organization_id, name, type_),
            )
            row = await cur.fetchone()
            await conn.commit()
            return row


async def get_or_create_counterparty(name: str) -> dict:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT * FROM counterparties WHERE lower(name) = lower(%s)", (name,)
            )
            row = await cur.fetchone()
            if row:
                return row

            await cur.execute(
                "INSERT INTO counterparties (name) VALUES (%s) RETURNING *",
                (name,),
            )
            row = await cur.fetchone()
            await conn.commit()
            return row


async def save_transaction(
    user_id: int,
    organization_id: int,
    type_: str,
    amount: float,
    currency: str,
    date: str,
    category_id: int | None,
    counterparty_id: int | None,
    is_offset: bool,
    raw_ai_log: dict,
) -> dict:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO transactions (
                    user_id, organization_id, type, amount, currency, date,
                    category_id, counterparty_id, is_offset,
                    offset_status, raw_ai_log
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    user_id,
                    organization_id,
                    type_,
                    amount,
                    currency,
                    date,
                    category_id,
                    counterparty_id,
                    is_offset,
                    "pending" if is_offset else None,
                    json.dumps(raw_ai_log, ensure_ascii=False),
                ),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def save_expense_participants(
    transaction_id: int, participants: list[dict]
) -> None:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            for participant in participants:
                await cur.execute(
                    """
                    INSERT INTO expense_participants (transaction_id, person_name, amount)
                    VALUES (%s, %s, %s)
                    """,
                    (transaction_id, participant["name"], participant["amount"]),
                )
        await conn.commit()


async def save_offset(
    source_transaction_id: int, counterparty_id: int, amount: float
) -> dict:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO counterparty_offsets (
                    source_transaction_id, counterparty_id, amount, status
                )
                VALUES (%s, %s, %s, 'pending')
                RETURNING *
                """,
                (source_transaction_id, counterparty_id, amount),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def get_open_offsets(counterparty_id: int) -> list[dict]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT * FROM counterparty_offsets
                WHERE counterparty_id = %s AND status = 'pending'
                ORDER BY created_at
                """,
                (counterparty_id,),
            )
            return await cur.fetchall()


async def apply_offsets(offset_ids: list[int], applied_to_transaction_id: int) -> None:
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE counterparty_offsets
                SET status = 'applied', applied_to_transaction_id = %s
                WHERE id = ANY(%s)
                """,
                (applied_to_transaction_id, offset_ids),
            )
        await conn.commit()


async def get_counterparty_balances() -> list[dict]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT
                    c.name AS counterparty_name,
                    COALESCE(SUM(o.amount) FILTER (WHERE o.status = 'pending'), 0) AS open_offset_amount,
                    COUNT(*) FILTER (WHERE o.status = 'pending') AS open_offset_count
                FROM counterparties c
                JOIN counterparty_offsets o ON o.counterparty_id = c.id
                GROUP BY c.id, c.name
                HAVING COUNT(*) FILTER (WHERE o.status = 'pending') > 0
                ORDER BY c.name
                """
            )
            return await cur.fetchall()


async def get_debt_summary() -> list[dict]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT
                    ep.person_name,
                    SUM(ep.amount) AS total_debt,
                    COUNT(*) AS total_expenses,
                    COUNT(*) FILTER (WHERE ep.is_paid = false) AS pending_returns
                FROM expense_participants ep
                WHERE ep.is_paid = false
                GROUP BY ep.person_name
                ORDER BY ep.person_name
                """
            )
            return await cur.fetchall()


async def mark_participant_paid(
    transaction_id: int, person_name: str, amount_paid: float | None
) -> dict | None:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT * FROM expense_participants
                WHERE transaction_id = %s AND person_name = %s
                """,
                (transaction_id, person_name),
            )
            participant = await cur.fetchone()
            if participant is None:
                return None

            final_amount = amount_paid if amount_paid is not None else participant["amount"]

            await cur.execute(
                """
                UPDATE expense_participants
                SET is_paid = TRUE, paid_date = NOW(), paid_amount = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (final_amount, participant["id"]),
            )
            row = await cur.fetchone()
        await conn.commit()
        return row


async def find_open_expense_by_person(person_name: str) -> dict | None:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT ep.*, t.date, t.amount AS transaction_amount
                FROM expense_participants ep
                JOIN transactions t ON t.id = ep.transaction_id
                WHERE ep.person_name = %s AND ep.is_paid = false
                ORDER BY t.date DESC
                LIMIT 1
                """,
                (person_name,),
            )
            return await cur.fetchone()


async def get_transactions_for_period(start_date: str, end_date: str) -> list[dict]:
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT
                    t.*,
                    o.name AS organization_name,
                    c.name AS category_name,
                    cp.name AS counterparty_name,
                    u.username AS created_by_username
                FROM transactions t
                JOIN organizations o ON o.id = t.organization_id
                LEFT JOIN categories c ON c.id = t.category_id
                LEFT JOIN counterparties cp ON cp.id = t.counterparty_id
                JOIN users u ON u.id = t.user_id
                WHERE t.date BETWEEN %s AND %s
                ORDER BY t.date, t.id
                """,
                (start_date, end_date),
            )
            return await cur.fetchall()


async def get_expense_participants_for_transactions(
    transaction_ids: list[int],
) -> list[dict]:
    if not transaction_ids:
        return []
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT * FROM expense_participants
                WHERE transaction_id = ANY(%s)
                ORDER BY transaction_id, person_name
                """,
                (transaction_ids,),
            )
            return await cur.fetchall()
