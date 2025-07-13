import streamlit as st
from datetime import datetime, timedelta, timezone
from content import survey, teamlead_view, settings, reports
from auth import get_user_by_email, register_user, is_team_lead, is_admin, hash_password, check_password, generate_token, save_token, get_user_by_token

st.set_page_config(page_title="Survey",  page_icon="✅", layout="wide", initial_sidebar_state="expanded")
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if "show_login" not in st.session_state:
    st.session_state.show_login = False
if "show_register" not in st.session_state:
    st.session_state.show_register = False
if "user" not in st.session_state:
    st.session_state.user = None

#############
query_params = st.query_params
token = query_params.get("token", "")
if token and not st.session_state.user:
    user = get_user_by_token(token)
    if user:
        st.session_state.user = user

# if "show_login" not in st.session_state:
#     st.session_state.show_login = False
# if "show_register" not in st.session_state:
#     st.session_state.show_register = False
# if "user" not in st.session_state:
#     st.session_state.user = None

user = st.session_state.user
#################



# ========== Without authorization ==========
if not user:
    survey.run()

    col1, col2 = st.columns(2)

    # with col1:
    #     if st.button("🔐 Login"):
    #         st.session_state.show_login = not st.session_state.show_login
    #         st.session_state.show_register = False

    # with col2:
    #     if st.button("📝 Register"):
    #         st.session_state.show_register = not st.session_state.show_register
    #         st.session_state.show_login = False

    col_space, col_buttons = st.columns([10, 2])  # подогнать ширину под нужды
    with col_buttons:
        col_login, col_register = st.columns([1, 1])
        with col_login:
            if st.button("🔐 Login"):
                st.session_state.show_login = not st.session_state.show_login
                st.session_state.show_register = False
        with col_register:
            if st.button("📝 Register"):
                st.session_state.show_register = not st.session_state.show_register
                st.session_state.show_login = False
            
    # ==== Login form ====

  
    if st.session_state.show_login:
        st.subheader("🔐 Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        hashed_pw = hash_password(login_password)
        #st.success(hashed_pw)
        #st.success(login_password)
        # st.success(user["password"])
        # hash_password(password)
        if st.button("Login now"):
            user = get_user_by_email(login_email)
            # if user and user["password"] == login_password: 
            if user and check_password(login_password, user["password"]):
                st.session_state.user = user
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")
                
    # ==== Registration form ====
    if st.session_state.show_register:
        st.subheader("📝 Register")
        reg_name = st.text_input("Name", key="reg_name")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")

        if st.button("Create account"):
            success = register_user(reg_name, reg_email, reg_password)
            if success:
                st.success("Registered successfully! Now log in.")
                st.session_state.show_register = False
                st.session_state.show_login = True
            else:
                st.error("User with this email already exists.")

# ========== After login ==========
else:
    st.sidebar.title("📋 Menu")
    options = ["Survey"]
    if is_team_lead(user):
        options.append("Team Lead")
    if is_admin(user):
        options.append("Settings")
        options.append("Reports")
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
        st.session_state.user = None
        st.success("Logged out.")
        st.rerun()
