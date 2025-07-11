import streamlit as st
from content import survey, teamlead_view, settings, reports
from auth import (
    get_user_by_email,
    register_user,
    is_team_lead,
    is_admin,
    hash_password,
    check_password,
    generate_token,
    get_user_by_token,
    save_token,
    delete_user_tokens,
)
from datetime import datetime, timedelta

st.set_page_config(page_title="Survey", page_icon="✅", layout="wide", initial_sidebar_state="expanded")

# === Скрытие UI ===
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# === Получение токена из ссылки ===
query_params = st.query_params
token = query_params.get("token", "")

# Если токен в ссылке есть и пользователь не авторизован
if token and not st.session_state.get("user"):
    user = get_user_by_token(token)
    if user:
        st.session_state.user = user

# Очистка user если токен не передан
if not token and "user" in st.session_state:
    del st.session_state.user

# Инициализация состояний
st.session_state.setdefault("show_login", False)
st.session_state.setdefault("show_register", False)
st.session_state.setdefault("user", None)

user = st.session_state.user

# ========== Без авторизации ==========
if not user:
    survey.run()

    col_space, col_buttons = st.columns([10, 2])
    with col_buttons:
        col_login, col_register = st.columns(2)
        with col_login:
            if st.button("🔐 Login"):
                st.session_state.show_login = not st.session_state.show_login
                st.session_state.show_register = False
        with col_register:
            if st.button("📝 Register"):
                st.session_state.show_register = not st.session_state.show_register
                st.session_state.show_login = False

    # === Форма входа ===
    if st.session_state.show_login:
        st.subheader("🔐 Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login now"):
            user = get_user_by_email(login_email)
            if user and check_password(login_password, user["password"]):
                token = generate_token(user["email"])
                expires_at = datetime.utcnow() + timedelta(days=1)
                save_token(token, user["id"], expires_at)
                redirect_url = f"?token={token}"
                st.markdown(f"<meta http-equiv='refresh' content='0; url={redirect_url}'>", unsafe_allow_html=True)
                st.stop()
            else:
                st.error("Invalid credentials")

    # === Форма регистрации ===
    if st.session_state.show_register:
        st.subheader("📝 Register")
        reg_name = st.text_input("Name", key="reg_name")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")

        if st.button("Create account"):
            success = register_user(reg_name, reg_email, reg_password)
            if success:
                user = get_user_by_email(reg_email)
                if user:
                    token = generate_token(user["email"])
                    expires_at = datetime.utcnow() + timedelta(days=1)
                    save_token(token, user["id"], expires_at)
                    redirect_url = f"?token={token}"
                    st.markdown(f"<meta http-equiv='refresh' content='0; url={redirect_url}'>", unsafe_allow_html=True)
                    st.stop()
            else:
                st.error("User with this email already exists.")

# ========== После входа ==========
else:
    st.sidebar.title("📋 Menu")
    options = ["Survey"]
    if is_team_lead(user):
        options.append("Team Lead")
    if is_admin(user):
        options.extend(["Settings", "Reports"])
    options.append("Logout")

    page = st.sidebar.radio("Navigation", options)

    if page == "Survey":
        survey.run()
    elif page == "Team Lead":
        teamlead_view.run()
    elif page == "Settings":
        settings.run()
    elif page == "Reports":
        reports.run()
    elif page == "Logout":
        delete_user_tokens(user["id"])
        st.session_state.clear()
        st.success("Logged out.")
        st.rerun()
