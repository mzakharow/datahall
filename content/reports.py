import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import date
from db import get_engine
from auth import is_admin

def run():
    st.title("📊 Technician Tasks Report")

    user = st.session_state.get("user")
    if not user or not is_admin(user):
        st.error("Access denied")
        return

    engine = get_engine()

    selected_date = st.date_input("Select date", value=date.today())
    show_latest_only = st.checkbox("Show current tasks", value=True)

    with engine.connect() as conn:
        if show_latest_only:
            query = """
                SELECT 
                    t.id,
                    t.technician_id,
                    tech.name AS technician,
                    tl.name AS team_lead,
                    loc.name AS location,
                    act.name AS activity,
                    t.rack,
                    t.timestamp
                FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (PARTITION BY technician_id ORDER BY timestamp DESC) AS rn
                    FROM technician_tasks
                    WHERE DATE(timestamp) = :selected_date
                ) t
                JOIN technicians tech ON tech.id = t.technician_id
                LEFT JOIN technicians tl ON tl.id = t.source
                LEFT JOIN locations loc ON loc.id = t.location_id
                LEFT JOIN activities act ON act.id = t.activity_id
                WHERE t.rn = 1
                ORDER BY t.timestamp DESC
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
                WHERE DATE(task.timestamp) = :selected_date
                ORDER BY task.timestamp DESC
            """

        rows = conn.execute(text(query), {"selected_date": selected_date}).fetchall()

    if not rows:
        st.info("No tasks found for the selected date.")
        return

    df = pd.DataFrame([dict(row._mapping) for row in rows])

    with st.expander("🔍 Filters"):
        for col in ["technician", "team_lead", "location", "activity", "rack"]:
            if col in df.columns:
                options = df[col].dropna().unique().tolist()
                selected = st.multiselect(f"Filter by {col}", options, key=f"filter_{col}")
                if selected:
                    df = df[df[col].isin(selected)]

    st.dataframe(df, use_container_width=True)
    st.caption(f"Total records: {len(df)}")
