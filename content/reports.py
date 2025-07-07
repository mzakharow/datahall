import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
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

    # Указываем временную зону сервера/клиента
    LOCAL_TIMEZONE = ZoneInfo("America/Chicago")
    now_local = datetime.now(LOCAL_TIMEZONE)
    today_local = now_local.date()

    selected_date_local = st.date_input("Select date", value=today_local)
    show_latest_only = st.checkbox("Show current tasks", value=True)

    # Начало и конец выбранного дня в локальной зоне
    start_local = datetime.combine(selected_date_local, datetime.min.time(), tzinfo=LOCAL_TIMEZONE)
    end_local = start_local + timedelta(days=1)

    # Преобразуем в UTC
    start_utc = start_local.astimezone(ZoneInfo("UTC"))
    end_utc = end_local.astimezone(ZoneInfo("UTC"))

    with engine.connect() as conn:
        if show_latest_only:
            query = """
                SELECT 
                    tech.id AS technician_id,
                    tech.name AS technician,
                    COALESCE(tl.name, '—') AS team_lead,
                    loc.name AS location,
                    act.name AS activity,
                    task.rack,
                    task.timestamp
                FROM technicians tech
                LEFT JOIN technicians tl ON tech.team_lead = tl.id
                LEFT JOIN (
                    SELECT *
                    FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (PARTITION BY technician_id ORDER BY timestamp DESC) AS rn
                        FROM technician_tasks
                        WHERE timestamp >= :start_utc AND timestamp < :end_utc
                    ) sub
                    WHERE rn = 1
                ) task ON task.technician_id = tech.id
                LEFT JOIN locations loc ON task.location_id = loc.id
                LEFT JOIN activities act ON task.activity_id = act.id
                WHERE tech.activ = true
                ORDER BY tech.name
            """
        else:
            query = """
                SELECT 
                    t.name AS technician,
                    tl.name AS team_lead,
                    l.name AS location,
                    a.name AS activity,
                    task.rack,
                    task.timestamp
                FROM technician_tasks task
                LEFT JOIN technicians t ON task.technician_id = t.id
                LEFT JOIN technicians tl ON task.source = tl.id
                LEFT JOIN locations l ON task.location_id = l.id
                LEFT JOIN activities a ON task.activity_id = a.id
                WHERE task.timestamp >= :start_utc AND task.timestamp < :end_utc
                ORDER BY task.timestamp DESC
            """

        rows = conn.execute(text(query), {
            "start_utc": start_utc,
            "end_utc": end_utc
        }).fetchall()

    if not rows:
        st.info("No tasks found for the selected date.")
        return

    df = pd.DataFrame([dict(row._mapping) for row in rows])

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(LOCAL_TIMEZONE)

    with st.expander("🔍 Filters"):
        for col in ["technician", "team_lead", "location", "activity", "rack"]:
            if col in df.columns:
                options = df[col].dropna().unique().tolist()
                selected = st.multiselect(f"Filter by {col}", options, key=f"filter_{col}")
                if selected:
                    df = df[df[col].isin(selected)]

    st.dataframe(df, use_container_width=True)
    st.caption(f"Total records: {len(df)}")
