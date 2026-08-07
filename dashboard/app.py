import datetime

import streamlit as st

import queries
import sections
from auth import check_password

st.set_page_config(page_title="Финансы — дашборд", layout="wide")

if not check_password():
    st.stop()

st.title("Финансы — дашборд")

orgs = queries.list_organizations()
org_options = {"Все объекты": None} | dict(zip(orgs["name"], orgs["id"]))

with st.sidebar:
    st.header("Фильтры")

    today = datetime.date.today()
    month_start = today.replace(day=1)
    date_range = st.date_input(
        "Период",
        value=(month_start, today),
        format="YYYY-MM-DD",
    )
    org_label = st.selectbox("Объект", options=list(org_options.keys()))

if len(date_range) != 2:
    st.stop()

start_date, end_date = date_range
organization_id = org_options[org_label]

summary = queries.get_summary(start_date.isoformat(), end_date.isoformat())
if organization_id is not None:
    summary = summary[summary["organization_name"] == org_label]

monthly = queries.get_monthly_series(
    start_date.isoformat(), end_date.isoformat(), organization_id
)
categories = queries.get_category_breakdown(
    start_date.isoformat(), end_date.isoformat(), organization_id
)
debts = queries.get_debt_summary()
offsets = queries.get_offset_balances()

sections.render_overview_metrics(summary)
sections.render_monthly_chart(monthly)
sections.render_category_chart(categories)
sections.render_debts_table(debts)
sections.render_offsets_table(offsets)
