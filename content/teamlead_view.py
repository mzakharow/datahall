import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, date
from db import get_engine

def run():
    st.title("👷 Team Lead Panel")
    engine = get_engine()
    user = st.session_state.get("user")
    if not user or not user.get("is_teamlead"):
        st.error("Access denied")
        return
    team_lead_id = user["id"]
    with engine.connect() as conn:
        # Техники в подчинении
        technicians = conn.execute(text("""
            SELECT id, name FROM technicians
            WHERE team_lead = :tl_id AND activ = true
            ORDER BY name
        """), {"tl_id": team_lead_id}).fetchall()

        locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name")).fetchall()
        activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name")).fetchall()

    if not technicians:
        st.info("You don't have a team.")
        return

    loc_options = {loc.name: loc.id for loc in locations}
    act_options = {act.name: act.id for act in activities}
    tech_options = {tech.name: tech.id for tech in technicians}
    tech_ids = [tech.id for tech in technicians]

    # Получение последних записей technician_tasks за сегодня
    latest_tasks = {}
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT technician_id, location_id, activity_id, rack
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY technician_id ORDER BY timestamp DESC) as rn
                FROM technician_tasks
                WHERE technician_id = ANY(:tech_ids) AND DATE(timestamp) = :today
            ) sub
            WHERE rn = 1"""), {
            "tech_ids": tech_ids,
            "today": date.today()
        }).fetchall()

        for row in rows:
            latest_tasks[row.technician_id] = dict(row._mapping)

    # Формируем таблицу
    df = pd.DataFrame([{
        "Technician": tech.name,
        "Location": next((loc.name for loc in locations if loc.id == latest_tasks.get(tech.id, {}).get("location_id")), list(loc_options.keys())[0]),
        "Activity": next((act.name for act in activities if act.id == latest_tasks.get(tech.id, {}).get("activity_id")), list(act_options.keys())[0]),
        "Rack": latest_tasks.get(tech.id, {}).get("rack", "")
    } for tech in technicians])

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        key="assignments_editor",
        column_config={
            "Location": st.column_config.SelectboxColumn("Location", options=list(loc_options.keys())),
            "Activity": st.column_config.SelectboxColumn("Activity", options=list(act_options.keys())),
            "Rack": st.column_config.TextColumn("Rack", max_chars=5)
        }
    )

    if st.button("💾 Save tasks"):
        with engine.begin() as conn:
            for _, row in edited_df.iterrows():
                tech_name = row["Technician"]
                loc_id = loc_options.get(row["Location"])
                act_id = act_options.get(row["Activity"])
                rack = str(row.get("Rack", "")).strip()[:5]

                if tech_id and loc_id and act_id:
                    conn.execute(text("""
                        INSERT INTO technician_tasks (technician_id, location_id, activity_id, rack, created_at)
                        VALUES (:tech_id, :loc_id, :act_id, :rack, :created_at)
                    """), {
                        "tech_id": tech_id,
                        "loc_id": loc_id,
                        "act_id": act_id,
                        "rack": rack,
                        "created_at": datetime.now()
                    })

        st.success("✅ Changes saved!")
        st.rerun()
