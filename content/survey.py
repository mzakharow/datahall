import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timezone
from sqlalchemy import text
from zoneinfo import ZoneInfo
from db import get_engine
from auth import get_user_by_email, encode_email, decode_email, generate_token, get_user_by_token
import pytz

def run():
    st.title("📋 Survey")

    engine = get_engine()
    query_params = st.query_params
    url_email = query_params.get("email", "").lower()
    # url_email = decode_email(query_params.get("email", "").lower())

    # query_params = st.query_params
    # token = query_params.get("token", "")  
    
    # if token:
    #     engine = get_engine()
    #     with engine.connect() as conn:
    #         result = conn.execute(text("""
    #             SELECT user_id, expires_at
    #             FROM auth_tokens
    #             WHERE token = :token
    #         """), {"token": token}).fetchone()

    #         if result:
    #             expires_at = result.expires_at.replace(tzinfo=timezone.utc)
    #             if datetime.now(timezone.utc) < expires_at:
    #                 user = get_user_by_token(token)
    #                 if user:
    #                     st.session_state.user = user
    #             else:
    #                 st.warning("⚠️ Token expired.")
    #         else:
    #             st.warning("⚠️ Invalid token.")
                

    if "email_checked" not in st.session_state:
        st.session_state.email_checked = False
    if "user_data" not in st.session_state:
        st.session_state.user_data = None
    if "email" not in st.session_state:
        st.session_state.email = url_email

    email = st.text_input("Enter email", value=st.session_state.email)
    st.session_state.email = email


    LOCAL_TIMEZONE = "America/Chicago"
    today_local = datetime.now(ZoneInfo(LOCAL_TIMEZONE)).date()

    LOCAL_TIMEZONE = "America/Chicago"
    timezone = pytz.timezone(LOCAL_TIMEZONE)
    today_local = datetime.now(ZoneInfo(LOCAL_TIMEZONE)).date()
    # start = datetime.combine(today_local, time.min).astimezone(ZoneInfo("UTC"))
    # end = datetime.combine(today_local, time.max).astimezone(ZoneInfo("UTC"))

    def load_last_task(user_id):
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT location_id, activity_id, cable_type_id, rack
                FROM technician_tasks
                WHERE technician_id = :tech_id
                  AND DATE(timestamp) = :today
                ORDER BY timestamp DESC
                LIMIT 1
            """), {
                "tech_id": user_id,
                # in query # AND timestamp >= :start AND timestamp < :end
                # "start": start,
                # "end": end
                "today": today_local,
                "tz": LOCAL_TIMEZONE
            }).first()

        if row:
            task = dict(row._mapping)
            st.session_state.last_location_id = task["location_id"]
            st.session_state.last_activity_id = task["activity_id"]
            st.session_state.last_cable_type_id = task["cable_type_id"]
            st.session_state.last_rack = task["rack"]
        else:
            st.session_state.last_location_id = None
            st.session_state.last_activity_id = None
            st.session_state.last_cable_type_id = None
            st.session_state.last_rack = ""

    if url_email and not st.session_state.email_checked:
        user = get_user_by_email(url_email)
        if user:
            st.session_state.user_data = user
            st.session_state.email_checked = True
            load_last_task(user["id"])
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
            load_last_task(row.id)
            st.success("Email verified!")
        else:
            st.error("User not found.")

    if st.session_state.email_checked:
        user = st.session_state.user_data

        with engine.connect() as conn:
            locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name")).fetchall()
            activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name")).fetchall()
            cable_types = conn.execute(text("SELECT id, name FROM cable_type ORDER BY name")).fetchall()
            racks = conn.execute(text("SELECT id, name, dh FROM racks ORDER BY name")).fetchall()

        loc_options = {loc.name: loc.id for loc in locations}
        act_options = {act.name: act.id for act in activities}
        cable_options = {ct.name: ct.id for ct in cable_types}
        racks_options = {f"{rack.name} ({rack.dh})": rack.id for rack in racks}

        act_id_to_name = {v: k for k, v in act_options.items()}
        cable_id_to_name = {v: k for k, v in cable_options.items()}
        rack_id_to_name = {v: k for k, v in racks_options.items()}

        default_loc = next((name for name, id_ in loc_options.items()
                            if id_ == st.session_state.get("last_location_id")), None)
        default_act = act_id_to_name.get(st.session_state.get("last_activity_id"))
        default_cable = cable_id_to_name.get(st.session_state.get("last_cable_type_id"))
        default_rack = rack_id_to_name.get(st.session_state.get("last_rack_id"))

        selected_location = st.selectbox("Select location", list(loc_options.keys()),
            index=list(loc_options.keys()).index(default_loc) if default_loc in loc_options else 0)

        selected_activity = st.selectbox("Select activity", list(act_options.keys()),
            index=list(act_options.keys()).index(default_act) if default_act in act_options else 0)

        selected_cable = st.selectbox("Select cable type", list(cable_options.keys()),
            index=list(cable_options.keys()).index(default_cable) if default_cable in cable_options else 0)

        # rack_input = st.text_input("Rack", value=st.session_state.get("last_rack", "")).strip()[:5]
        selected_rack = st.selectbox("Select rack", list(racks_options.keys()),
            index=list(racks_options.keys()).index(default_cable) if default_cable in racks_options else 0)

        if st.button("Confirm"):
            confirmed_email = st.session_state.user_data["email"].strip().lower()
            current_email = st.session_state.email.strip().lower()

            if current_email != confirmed_email:
                st.error("⚠️ Email doesn't match the verified one. Please use the confirmed email.")
            else:
                # now = datetime.now()
                now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
                now_in_timezone = now_utc.astimezone(timezone)
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO technician_tasks (
                            technician_id, location_id, activity_id, cable_type_id, rack_id, source, timestamp
                        )
                        VALUES (:technician_id, :location_id, :activity_id, :cable_type_id, :rack_id, :source, :timestamp)
                    """), {
                        "technician_id": user["id"],
                        "location_id": loc_options[selected_location],
                        "activity_id": act_options[selected_activity],
                        "cable_type_id": cable_options[selected_cable],
                        "rack_id": racks_options[selected_rack],
                        "source": user["id"],
                        "timestamp": now_in_timezone
                    })

                st.success("Saved!")
                st.rerun()
