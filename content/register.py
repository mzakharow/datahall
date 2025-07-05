import streamlit as st
from auth import register_user

def register_page():
    st.title("📝 Register")

    name = st.text_input("Name")
    email = st.text_input("Email")
    if st.button("Register"):
        if name and email:
            success = register_user(name, email)
            if success:
                st.success("Registration successful! You can now log in.")
            else:
                st.error("Email already exists.")
        else:
            st.warning("Fill in both fields")

if "user" not in st.session_state:
    register_page()
