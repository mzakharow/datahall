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

            with engine.connect() as conn:
                last_tasks = conn.execute(text("""
                    SELECT location_id, rack,
                           array_agg(DISTINCT activity_id) AS activity_ids,
                           array_agg(DISTINCT cable_type_id) AS cable_type_ids
                    FROM technician_tasks
                    WHERE technician_id = :tech_id AND DATE(timestamp) = :today
                    GROUP BY location_id, rack
                    ORDER BY MAX(timestamp) DESC
                    LIMIT 1
                """), {
                    "tech_id": user["id"],
                    "today": date.today()
                }).first()

                if last_tasks:
                    st.session_state.last_location_id = last_tasks.location_id
                    st.session_state.last_activity_ids = last_tasks.activity_ids or []
                    st.session_state.last_cable_type_ids = last_tasks.cable_type_ids or []
                    st.session_state.last_rack = last_tasks.rack
                else:
                    st.session_state.last_location_id = None
                    st.session_state.last_activity_ids = []
                    st.session_state.last_cable_type_ids = []
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
            st.success("Email verified!")

    if st.session_state.email_checked:
        user = st.session_state.user_data

        with engine.connect() as conn:
            locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name")).fetchall()
            activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name")).fetchall()
            cable_types = conn.execute(text("SELECT id, name FROM cable_type ORDER BY name")).fetchall()

        loc_options = {loc.name: loc.id for loc in locations}
        act_options = {act.name: act.id for act in activities}
        cable_options = {ct.name: ct.id for ct in cable_types}

        act_id_to_name = {v: k for k, v in act_options.items()}
        cable_id_to_name = {v: k for k, v in cable_options.items()}

        default_loc = next((name for name, id_ in loc_options.items()
                            if id_ == st.session_state.get("last_location_id")), None)
        default_acts = [act_id_to_name.get(i) for i in st.session_state.get("last_activity_ids", []) if i in act_id_to_name]
        default_cables = [cable_id_to_name.get(i) for i in st.session_state.get("last_cable_type_ids", []) if i in cable_id_to_name]

        selected_location = st.selectbox("Select location", list(loc_options.keys()), 
            index=list(loc_options.keys()).index(default_loc) if default_loc in loc_options else 0)

        selected_activities = st.multiselect("Select activities", list(act_options.keys()), default=default_acts)
        selected_cables = st.multiselect("Select cable types", list(cable_options.keys()), default=default_cables)

        rack_input = st.text_input("Rack", value=st.session_state.get("last_rack", "")).strip()[:5]

        if st.button("Confirm"):
            confirmed_email = st.session_state.user_data["email"].strip().lower()
            current_email = st.session_state.email.strip().lower()

            if current_email != confirmed_email:
                st.error("⚠️ Email doesn't match the verified one.")
            elif not selected_activities or not selected_cables:
                st.warning("Please select at least one activity and one cable type.")
            else:
                now = datetime.now()
                with engine.begin() as conn:
                    for act_name in selected_activities:
                        for cable_name in selected_cables:
                            conn.execute(text("""
                                INSERT INTO technician_tasks (
                                    technician_id, location_id, activity_id, cable_type_id, rack, source, timestamp
                                ) VALUES (
                                    :technician_id, :location_id, :activity_id, :cable_type_id, :rack, :source, :timestamp
                                )
                            """), {
                                "technician_id": user["id"],
                                "location_id": loc_options[selected_location],
                                "activity_id": act_options[act_name],
                                "cable_type_id": cable_options[cable_name],
                                "rack": rack_input,
                                "source": user["id"],
                                "timestamp": now
                            })

                st.success("Saved!")
