import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime
from db import get_engine

def run():
    st.title("👷 Team Lead Panel")

    user = st.session_state.get("user")
    if not user or not user.get("is_teamlead"):
        st.error("Access denied")
        return

    team_lead_id = user["id"]

    # Получение подчинённых техников
    with get_engine().connect() as conn:
        technicians = conn.execute(text("""
            SELECT id, name FROM technicians
            WHERE team_lead = :tl_id AND activ = true
            ORDER BY name
        """), {"tl_id": team_lead_id}).fetchall()

        locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name")).fetchall()
        activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name")).fetchall()

    if not technicians:
        st.info("У вас пока нет подчинённых.")
        return

    loc_options = {loc.name: loc.id for loc in locations}
    act_options = {act.name: act.id for act in activities}
    tech_options = {tech.name: tech.id for tech in technicians}

    # Подготовка начального DataFrame
    df = pd.DataFrame([{
        "Technician": tech.name,
        "Location": list(loc_options.keys())[0],
        "Activity": list(act_options.keys())[0]
    } for tech in technicians])

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        key="assignments_editor",
        column_config={
            "Location": st.column_config.SelectboxColumn(
                "Location", options=list(loc_options.keys())
            ),
            "Activity": st.column_config.SelectboxColumn(
                "Activity", options=list(act_options.keys())
            ),
        }
    )

    if st.button("💾 Назначить задачи"):
        with get_engine().begin() as conn:
            for _, row in edited_df.iterrows():
                tech_name = row["Technician"]
                tech_id = tech_options.get(tech_name)
                loc_id = loc_options.get(row["Location"])
                act_id = act_options.get(row["Activity"])

                if tech_id and loc_id and act_id:
                    conn.execute(text("""
                        INSERT INTO technician_assignments (technician_id, team_lead_id, location_id, activity_id, created_at)
                        VALUES (:tech_id, :tl_id, :loc_id, :act_id, :created_at)
                    """), {
                        "tech_id": tech_id,
                        "tl_id": team_lead_id,
                        "loc_id": loc_id,
                        "act_id": act_id,
                        "created_at": datetime.now()
                    })

        st.success("Назначения сохранены ✅")
        st.rerun()
    # Таблица уже назначенных задач
    