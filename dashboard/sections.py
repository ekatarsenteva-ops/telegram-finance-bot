import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Categorical slots 1/2 from the dataviz reference palette (light mode).
STATUS_COLORS = {
    "Приход": "#2a78d6",
    "Расход": "#eb6834",
}


def render_overview_metrics(summary: pd.DataFrame) -> None:
    st.subheader("Итого за период")

    if summary.empty:
        st.info("Нет операций за выбранный период.")
        return

    for org_name, org_df in summary.groupby("organization_name"):
        st.markdown(f"**{org_name}**")
        totals = org_df.set_index("status_label")["total"]
        income = totals.get("Приход", 0)
        expense = totals.get("Расход", 0)
        cols = st.columns(3)
        cols[0].metric("Приход", f"{income:,.0f} ₽".replace(",", " "))
        cols[1].metric("Расход", f"{expense:,.0f} ₽".replace(",", " "))
        cols[2].metric("Баланс", f"{income - expense:,.0f} ₽".replace(",", " "))


def render_monthly_chart(monthly: pd.DataFrame) -> None:
    st.subheader("Динамика по месяцам")

    if monthly.empty:
        st.info("Нет данных для графика.")
        return

    fig = go.Figure()
    for status_label, color in STATUS_COLORS.items():
        series = monthly[monthly["status_label"] == status_label]
        fig.add_trace(
            go.Bar(
                x=series["month"],
                y=series["total"],
                name=status_label,
                marker_color=color,
            )
        )

    fig.update_layout(
        barmode="group",
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font_color="#0b0b0b",
        legend_title_text="",
        margin=dict(t=20, b=20, l=20, r=20),
    )
    fig.update_xaxes(gridcolor="#e1e0d9", tickformat="%b %Y")
    fig.update_yaxes(gridcolor="#e1e0d9")
    st.plotly_chart(fig, use_container_width=True)


def render_category_chart(categories: pd.DataFrame) -> None:
    st.subheader("Расходы по категориям")

    if categories.empty:
        st.info("Нет расходов за выбранный период.")
        return

    fig = go.Figure(
        go.Bar(
            x=categories["total"],
            y=categories["category_name"],
            orientation="h",
            marker_color=STATUS_COLORS["Расход"],
        )
    )
    fig.update_layout(
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font_color="#0b0b0b",
        margin=dict(t=20, b=20, l=20, r=20),
        yaxis=dict(autorange="reversed"),
    )
    fig.update_xaxes(gridcolor="#e1e0d9")
    fig.update_yaxes(gridcolor="#e1e0d9")
    st.plotly_chart(fig, use_container_width=True)


def render_debts_table(debts: pd.DataFrame) -> None:
    st.subheader("Открытые долги участников")

    if debts.empty:
        st.info("Открытых долгов нет.")
        return

    st.dataframe(
        debts.rename(
            columns={
                "person_name": "Имя",
                "total_debt": "Сумма долга",
                "total_expenses": "Всего расходов",
                "pending_returns": "Не возвращено",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def render_offsets_table(offsets: pd.DataFrame) -> None:
    st.subheader("Открытые взаимозачёты")

    if offsets.empty:
        st.info("Открытых взаимозачётов нет.")
        return

    st.dataframe(
        offsets.rename(
            columns={
                "counterparty_name": "Контрагент",
                "open_offset_amount": "Сумма",
                "open_offset_count": "Кол-во",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )
