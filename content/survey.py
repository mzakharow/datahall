import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from db import get_engine
from auth import get_user_by_email

def run():
    st.title("📋 Survey")

    engine = get_engine()

    query_params = st.query_params
    url_email = query_params.get("email", "").lower()
    
    if "email_checked" not in st.session_state:
        st.session_state.email_checked = False
    if "user_data" not in st.session_state:
        st.session_state.user_data = None
    if "email" not in st.session_state:
        st.session_state.email = url_email

    query_params = st.query_params
    if "email" not in st.session_state:
        st.session_state.email = query_params.get("email", "")

    email = st.text_input("Enter email", value=st.session_state.email)
    st.session_state.email = email

    if url_email and not st.session_state.email_checked:
        user = get_user_by_email(url_email)
        if user:
            st.session_state.user_data = user
            st.session_state.email_checked = True
            st.success("Email auto-verified from link!")
        else:
            st.error("User not found.")

    if st.button("Check email"):
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM technicians WHERE LOWER(email) = :email"),
                {"email": email.lower()}
            ).first()

        if row:
            st.session_state.email_checked = True
            st.session_state.user_data = dict(row._mapping)
            st.success("Email success!")
        else:
            st.error("Email doesn't exist")

    if st.session_state.email_checked:
        user = st.session_state.user_data
        with engine.connect() as conn:
            locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name")).fetchall()
            activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name")).fetchall()

        loc_options = {loc.name: loc.id for loc in locations}
        act_options = {act.name: act.id for act in activities}

        selected_location = st.selectbox("Select location", list(loc_options.keys()))
        selected_activity = st.selectbox("Select activity", list(act_options.keys()))

        if st.button("Go"):
            response = {
                "email": user["email"],
                "technician_id": user["id"],
                "location_id": loc_options[selected_location],
                "activity_id": act_options[selected_activity],
                "timestamp": datetime.now()
            }

            # Save to DB (optional)
            # with engine.begin() as conn:
            #     conn.execute(text("""
            #         INSERT INTO technician_responses (technician_id, location_id, activity_id, timestamp)
            #         VALUES (:technician_id, :location_id, :activity_id, :timestamp)
            #     """), response)

            st.success("Saved!")
            st.json(response)
