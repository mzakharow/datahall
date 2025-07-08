import streamlit as st
import pandas as pd
from datetime import datetime, date
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

    email = st.text_input("Enter email", value=st.session_state.email)
    st.session_state.email = email

    if url_email and not st.session_state.email_checked:
        user = get_user_by_email(url_email)
        if user:
            st.session_state.user_data = user
            st.session_state.email_checked = True
            st.success("Email auto-verified from link!")
           
            with engine.connect() as conn:
                latest_task = conn.execute(text("""
                    SELECT location_id, activity_id, rack 
                    FROM technician_tasks
                    WHERE technician_id = :tech_id AND DATE(timestamp) = :today
                    ORDER BY timestamp DESC
                    LIMIT 1
                """), {
                    "tech_id": user["id"],
                    "today": date.today()
                }).first()

                if latest_task:
                    st.session_state.last_location_id = latest_task.location_id
                    st.session_state.last_activity_id = latest_task.activity_id
                    st.session_state.last_rack = latest_task.rack
                else:
                    st.session_state.last_location_id = None
                    st.session_state.last_activity_id = None
                    st.success(st.session_state.last_activity_id)
                    st.success(None)
                    st.session_state.last_rack = ""
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

            with engine.connect() as conn:
                latest_task = conn.execute(text("""
                    SELECT location_id, activity_id, rack 
                    FROM technician_tasks
                    WHERE technician_id = :tech_id AND DATE(timestamp) = :today
                    ORDER BY timestamp DESC
                    LIMIT 1
                """), {
                    "tech_id": st.session_state.user_data["id"],
                    "today": date.today()
                }).first()

                if latest_task:
                    st.session_state.last_location_id = latest_task.location_id
                    st.session_state.last_activity_id = latest_task.activity_id
                    st.session_state.last_rack = latest_task.rack
                else:
                    st.session_state.last_location_id = None
                    st.session_state.last_activity_id = None
                    st.session_state.last_rack = ""
        else:
            st.error("Email doesn't exist")

    if st.session_state.email_checked:
        user = st.session_state.user_data

        with engine.connect() as conn:
            locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name")).fetchall()
            activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name")).fetchall()

        loc_options = {loc.name: loc.id for loc in locations}
        act_options = {act.name: act.id for act in activities}

        default_loc = next((name for name, id_ in loc_options.items()
                            if id_ == st.session_state.get("last_location_id")), None)

        default_act = next((name for name, id_ in act_options.items()
                            if id_ == st.session_state.get("last_activity_id")), None)

        selected_location = st.selectbox("Select location", list(loc_options.keys()), 
            index=list(loc_options.keys()).index(default_loc) if default_loc in loc_options else 0)

        selected_activity = st.selectbox("Select activity", list(act_options.keys()), 
            index=list(act_options.keys()).index(default_act) if default_act in act_options else 0)

        rack_input = st.text_input("Rack", value=st.session_state.get("last_rack", "")).strip()[:5]

        if st.button("Confirm"):
            confirmed_email = st.session_state.user_data["email"].strip().lower()
            current_email = st.session_state.email.strip().lower()

            if current_email != confirmed_email:
                st.error("⚠️ Email doesn't match the verified one. Please use the confirmed email.")
            else:
                response = {
                    "email": confirmed_email,
                    "technician_id": user["id"],
                    "location_id": loc_options[selected_location],
                    "activity_id": act_options[selected_activity],
                    "rack": rack_input,
                    "timestamp": datetime.now()
                }

                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO technician_tasks (technician_id, location_id, activity_id, rack, source, timestamp)
                        VALUES (:technician_id, :location_id, :activity_id, :rack, :technician_id, :timestamp)
                    """), response)

                st.success("Saved!")
                st.json(response)
