import streamlit as st


def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.title("Финансы — вход")
    password = st.text_input("Пароль", type="password")

    if not password:
        return False

    if password == st.secrets["dashboard_password"]:
        st.session_state["authenticated"] = True
        st.rerun()

    st.error("Неверный пароль")
    return False
