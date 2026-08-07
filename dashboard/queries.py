import pandas as pd
import streamlit as st

from db import run_query

STATUS_LABELS = {
    "income": "Приход",
    "incoming_payment": "Приход",
    "expense": "Расход",
}


@st.cache_data(ttl=300)
def list_organizations() -> pd.DataFrame:
    return run_query("SELECT id, name FROM organizations ORDER BY id")


STATUS_CASE_SQL = """
    CASE t.type
        WHEN 'expense' THEN 'Расход'
        ELSE 'Приход'
    END
"""


@st.cache_data(ttl=300)
def get_summary(start: str, end: str) -> pd.DataFrame:
    return run_query(
        f"""
        SELECT
            o.name AS organization_name,
            {STATUS_CASE_SQL} AS status_label,
            SUM(t.amount) AS total
        FROM transactions t
        JOIN organizations o ON o.id = t.organization_id
        WHERE t.date BETWEEN %s AND %s
        GROUP BY o.name, status_label
        ORDER BY o.name, status_label
        """,
        (start, end),
    )


@st.cache_data(ttl=300)
def get_monthly_series(start: str, end: str, organization_id: int | None) -> pd.DataFrame:
    return run_query(
        f"""
        SELECT
            date_trunc('month', t.date)::date AS month,
            {STATUS_CASE_SQL} AS status_label,
            SUM(t.amount) AS total
        FROM transactions t
        WHERE t.date BETWEEN %s AND %s
          AND (%s::int IS NULL OR t.organization_id = %s)
        GROUP BY month, status_label
        ORDER BY month
        """,
        (start, end, organization_id, organization_id),
    )


@st.cache_data(ttl=300)
def get_category_breakdown(
    start: str, end: str, organization_id: int | None
) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            COALESCE(c.name, 'Без категории') AS category_name,
            SUM(t.amount) AS total
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.type = 'expense'
          AND t.date BETWEEN %s AND %s
          AND (%s::int IS NULL OR t.organization_id = %s)
        GROUP BY category_name
        ORDER BY total DESC
        """,
        (start, end, organization_id, organization_id),
    )


@st.cache_data(ttl=300)
def get_debt_summary() -> pd.DataFrame:
    return run_query(
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


@st.cache_data(ttl=300)
def get_offset_balances() -> pd.DataFrame:
    return run_query(
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
