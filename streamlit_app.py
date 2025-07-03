import streamlit as st
import pandas as pd
from datetime import datetime

st.title("Work location")

# Загрузка данных сотрудников (можно заменить на чтение из Google Sheets или БД)
# df = pd.read_csv("employees_data.csv")  # Таблица с email и вариантами

# Состояние сессии
if "email_checked" not in st.session_state:
    st.session_state.email_checked = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# Ввод email
# email = st.text_input("email")
# email = 'sdsdsd@dsds.com'

query_params = st.query_params
uemail = query_params.get("email", 'Enter your email')

#  email = st.text_input("Input email", value=st.session_state.email)
email = st.text_input("Enter your email", value=uemail)

row = {'task_options': 'DH', 'client_options': 'su'}
if st.button("Check email"):
    #row = df[df['employee_email'] == email]
    
    if row:
    #if not row.empty:
        st.session_state.email_checked = True
        # st.session_state.user_data = row.squeeze()
        st.session_state.user_data = 1
        st.success("Email checked!")
    else:
        st.error("Email doesn't exist")

# Показываем поля только если email подтвержден
# if st.session_state.email_checked and st.session_state.user_data is not None:
if st.session_state.email_checked:
    # user_data = st.session_state.user_data
    # tasks = user_data['task_options'].split(',')
    # clients = user_data['client_options'].split(',')
    tasks = row['task_options'].split(',')
    clients = row['client_options'].split(',')

    selected_task = st.selectbox("Choose location", tasks)
    selected_client = st.selectbox("Choose sublocation", clients)

    if st.button("Send"):
        # Пример сохранения данных — заменить на insert в БД
        response = {
            "email": email,
            "task": selected_task,
            "client": selected_client,
            "timestamp": datetime.now().isoformat()
        }

        st.success("Success!")
        st.json(response)  # Показываем данные (можно убрать)
