import pandas as pd
import psycopg
import streamlit as st


@st.cache_resource
def get_connection() -> psycopg.Connection:
    return psycopg.connect(st.secrets["database_url"], autocommit=True)


def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    except psycopg.OperationalError:
        get_connection.clear()
        conn = get_connection()
        return pd.read_sql(sql, conn, params=params)
