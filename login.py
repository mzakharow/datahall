import streamlit as st
from auth import get_user_by_email

def login_page():
    st.title("🔐 Login")

    email = st.text_input("Email")
    if st.button("Login"):
        user = get_user_by_email(email)
        if user:
            st.session_state.user = user
            st.success("Logged in successfully!")
        else:
            st.error("User not found")

if "user" not in st.session_state:
    login_page()
