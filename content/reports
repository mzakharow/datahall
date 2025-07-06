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

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT t.name AS technician, tl.name AS team_lead,
                   l.name AS location, a.name AS activity,
                   task.rack, task.timestamp
            FROM technician_tasks task
            LEFT JOIN technicians t ON task.technician_id = t.id
            LEFT JOIN technicians tl ON task.source = tl.id
            LEFT JOIN locations l ON task.location_id = l.id
            LEFT JOIN activities a ON task.activity_id = a.id
            WHERE DATE(task.timestamp) = :selected_date
            ORDER BY task.timestamp DESC
        """), {"selected_date": selected_date}).fetchall()

    if not rows:
        st.info("No tasks found for the selected date.")
        return

    df = pd.DataFrame([dict(row._mapping) for row in rows])

    # Фильтры по полям
    with st.expander("🔍 Filters"):
        for col in ["technician", "team_lead", "location", "activity", "rack"]:
            options = df[col].dropna().unique().tolist()
            selected = st.multiselect(f"Filter by {col}", options)
            if selected:
                df = df[df[col].isin(selected)]

    st.dataframe(df, use_container_width=True)
    st.caption(f"Total records: {len(df)}")
