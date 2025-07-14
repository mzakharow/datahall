import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime
from db import get_engine
from auth import is_admin
from zoneinfo import ZoneInfo

def run():
    st.title("📊 Technician Tasks Report")

    user = st.session_state.get("user")
    if not user or not is_admin(user):
        st.error("Access denied")
        return

    engine = get_engine()

    LOCAL_TIMEZONE = "America/Chicago"
    now_local = datetime.now(ZoneInfo(LOCAL_TIMEZONE))
    today_local = now_local.date()

    selected_date = st.date_input("Select date", value=today_local)
    show_latest_only = st.checkbox("Show current tasks only (1 per tech)", value=True)

    with engine.connect() as conn:
        if show_latest_only:
            query = """
                SELECT 
                    tech.id AS technician_id,
                    tech.name AS technician,
                    COALESCE(tl.name, '—') AS team_lead,
                    loc.name AS location,
                    act.name AS activity,
                    ct.name AS cable_type,
                    task.quantity,
                    task.percent,
                    task.rack,
                    COALESCE(src.name, '—') AS created_by,
                    task.timestamp
                FROM technicians tech
                LEFT JOIN technicians tl ON tech.team_lead = tl.id
                LEFT JOIN (
                       SELECT *
                    FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (PARTITION BY technician_id ORDER BY timestamp DESC) AS rn
                        FROM technician_tasks
                        WHERE DATE(timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :selected_date
                    ) sub
                    WHERE rn = 1
                ) task ON task.technician_id = tech.id
                LEFT JOIN technicians src ON task.source = src.id
                LEFT JOIN locations loc ON task.location_id = loc.id
                LEFT JOIN activities act ON task.activity_id = act.id
                LEFT JOIN cable_type ct ON task.cable_type_id = ct.id
                WHERE tech.activ = true
                ORDER BY tech.name
            """
        else:
            query = """
                SELECT 
                    t.name AS technician,
                    COALESCE(tl.name, '—') AS team_lead,
                    l.name AS location,
                    a.name AS activity,
                    ct.name AS cable_type,
                    task.quantity,
                    task.percent,
                    task.rack,
                    COALESCE(src.name, '—') AS created_by,
                    task.timestamp
                FROM technician_tasks task
                LEFT JOIN technicians t ON task.technician_id = t.id
                LEFT JOIN technicians tl ON t.team_lead = tl.id         
                LEFT JOIN technicians src ON task.source = src.id 
                LEFT JOIN locations l ON task.location_id = l.id
                LEFT JOIN activities a ON task.activity_id = a.id
                LEFT JOIN cable_type ct ON task.cable_type_id = ct.id
                WHERE DATE(task.timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :selected_date
                ORDER BY task.timestamp DESC
            """

        rows = conn.execute(text(query), {
            "selected_date": selected_date
        }).fetchall()

    if not rows:
        st.info("No tasks found for the selected date.")
        return

    df = pd.DataFrame([dict(row._mapping) for row in rows])

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(ZoneInfo(LOCAL_TIMEZONE))

    with st.expander("🔍 Filters"):
        for col in ["technician", "team_lead", "location", "activity", "rack"]:
            if col in df.columns:
                options = df[col].dropna().unique().tolist()
                selected = st.multiselect(f"Filter by {col}", options, key=f"filter_{col}")
                if selected:
                    df = df[df[col].isin(selected)]

    st.dataframe(df, use_container_width=True)
    st.caption(f"Total records: {len(df)}")


    with engine.connect() as conn:
        dhs = conn.execute(text("SELECT DISTINCT dh FROM racks ORDER BY dh")).fetchall()
        dh_options = [row.dh for row in dhs if row.dh]

    selected_dh = st.selectbox("📍 Select Datahall (DH)", dh_options)

    if selected_dh:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    r.name AS rack_name,
                    r.dh,
                    rs.position,
                    a.name AS activity,
                    ct.name AS cable_type,
                    s.name AS status,
                    rs.quantity,
                    rs.percent,
                    t.name AS created_by,
                    rs.timestamp
                FROM rack_states rs
                LEFT JOIN racks r ON rs.rack_id = r.id
                LEFT JOIN activities a ON rs.activity_id = a.id
                LEFT JOIN cable_type ct ON rs.cable_type_id = ct.id
                LEFT JOIN statuses s ON rs.status_id = s.id
                LEFT JOIN technicians t ON rs.created_by = u.id
                WHERE r.dh = :selected_dh
                ORDER BY rs.timestamp DESC
            """), {"selected_dh": selected_dh})

            rows = result.fetchall()
            if rows:
                df = pd.DataFrame([dict(row._mapping) for row in rows])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No data for selected DH.")
