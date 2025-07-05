import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# Подключение к БД
from auth import engine

def run():
    st.title("🛠️ Assign Tasks to Technicians")

    user = st.session_state.get("user")
    if not user:
        st.warning("You must be logged in to view this page.")
        return

    team_lead_id = user.get("id")

    # Получаем техников, которые относятся к текущему тимлиду
    with engine.connect() as conn:
        techs = conn.execute(
            text("""
                SELECT id, name FROM technicians
                WHERE team_lead = :tl_id AND activ = true
                ORDER BY name
            """), {"tl_id": team_lead_id}
        ).fetchall()

        locations = conn.execute(
            text("SELECT id, name FROM locations ORDER BY name")
        ).fetchall()

        activities = conn.execute(
            text("SELECT id, name FROM activities ORDER BY name")
        ).fetchall()

    if not techs:
        st.info("No technicians assigned to you yet.")
        return

    # Создание формы назначения
    with st.form("assign_form"):
        selected_tech = st.selectbox("👷 Technician", [f"{t.id} - {t.name}" for t in techs])
        selected_location = st.selectbox("📍 Location", [l.name for l in locations])
        selected_activity = st.selectbox("📋 Activity", [a.name for a in activities])
        submitted = st.form_submit_button("Assign Task")

        if submitted:
            tech_id = int(selected_tech.split(" - ")[0])
            location_id = next(l.id for l in locations if l.name == selected_location)
            activity_id = next(a.id for a in activities if a.name == selected_activity)

            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO technician_assignments (technician_id, team_lead_id, location_id, activity_id)
                        VALUES (:tech, :tl, :loc, :act)
                    """),
                    {
                        "tech": tech_id,
                        "tl": team_lead_id,
                        "loc": location_id,
                        "act": activity_id
                    }
                )

            st.success("✅ Task assigned successfully")

    # Таблица уже назначенных задач
    """with engine.connect() as conn:
        assigned = conn.execute(
            text("""
                SELECT t.name AS technician, l.name AS location, a.name AS activity
                FROM technician_assignments ta
                JOIN technicians t ON ta.technician_id = t.id
                JOIN locations l ON ta.location_id = l.id
                JOIN activities a ON ta.activity_id = a.id
                WHERE ta.team_lead_id = :tl_id
                ORDER BY technician
            """),
            {"tl_id": team_lead_id}
        ).fetchall()

    if assigned:
        df = pd.DataFrame(assigned)
        st.subheader("📑 Current Assignments")
        st.dataframe(df, use_container_width=True)"""