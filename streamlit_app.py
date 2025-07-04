import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text

# Установка параметров страницы и скрытие лишнего
st.set_page_config(
    page_title="Опрос сотрудников",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Подключение к базе данных
db = st.secrets["database"]
engine = create_engine(
    f"postgresql+psycopg2://{db.user}:{db.password}@{db.host}:{db.port}/{db.dbname}"
)

# Состояние сессии
if "email_checked" not in st.session_state:
    st.session_state.email_checked = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# ======================= Страницы ==========================

def user_survey_page():
    st.title("📍 Work location")

    # Получение email из URL
    query_params = st.query_params
    uemail = query_params.get("email", 'Enter your email')
    email = st.text_input("Enter your email", value=uemail)

    # Имитация получения вариантов (заменить на SELECT из БД при необходимости)
    row = {'task_options': 'DH,Super Core,Warehouse', 'client_options': '5,6,A,B'}

    if st.button("Check email"):
        if row:
            st.session_state.email_checked = True
            st.session_state.user_data = 1  # или данные пользователя
            st.session_state.email = email
            st.success("Email checked!")
        else:
            st.error("Email doesn't exist")

    if st.session_state.email_checked:
        tasks = row['task_options'].split(',')
        clients = row['client_options'].split(',')

        selected_task = st.selectbox("Choose location", tasks)
        selected_client = st.selectbox("Choose sublocation", clients)

        if st.button("Send"):
            response = {
                "email": email,
                "task": selected_task,
                "client": selected_client,
                "timestamp": datetime.now().isoformat()
            }

            st.success("Success!")
            st.json(response)

def locations_page():
    st.title("🗂 Управление локациями (locations)")

    # Загрузим текущие локации
    with engine.connect() as conn:
        df = pd.read_sql("SELECT id, name FROM locations ORDER BY id", conn)

    st.subheader("📋 Список локаций")
    st.dataframe(df)

    # ➕ Добавление
    st.subheader("Добавить новую локацию")
    new_name = st.text_input("Название новой локации")

    if st.button("Добавить"):
        if new_name:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO locations (name) VALUES (:name)"), {"name": new_name})
            st.success(f"Локация '{new_name}' добавлена!")
            st.experimental_rerun()
        else:
            st.warning("Введите название")

    # ✏️ Редактирование
    st.subheader("Редактировать существующую локацию")
    loc_names = df.set_index("id")["name"].to_dict()
    selected_id = st.selectbox("Выберите локацию", options=loc_names.keys(), format_func=lambda x: loc_names[x])
    new_value = st.text_input("Новое название", value=loc_names[selected_id])

    if st.button("Сохранить изменения"):
        with engine.begin() as conn:
            conn.execute(text("UPDATE locations SET name = :n WHERE id = :i"), {"n": new_value, "i": selected_id})
        st.success("Локация обновлена")
        st.experimental_rerun()

    # 🗑️ Удаление
    st.subheader("Удалить локацию")
    if st.button("Удалить выбранную локацию"):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM locations WHERE id = :i"), {"i": selected_id})
        st.success("Локация удалена")
        st.experimental_rerun()

# ======================= Навигация ==========================

st.sidebar.title("Навигация")
page = st.sidebar.radio("Страницы", ["Опрос", "Локации"])

if page == "Опрос":
    user_survey_page()
elif page == "Локации":
    locations_page()
