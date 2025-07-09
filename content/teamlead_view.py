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
    show_all = st.checkbox("👥 Show all technicians", value=False)

    with engine.connect() as conn:
        if show_all:
            technicians = conn.execute(text("""
                SELECT id, name FROM technicians
                WHERE activ = true
                ORDER BY name
            """)).fetchall()
        else:
            technicians = conn.execute(text("""
                SELECT id, name FROM technicians
                WHERE team_lead = :tl_id AND activ = true
                ORDER BY name
            """), {"tl_id": team_lead_id}).fetchall()

        locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name NULLS FIRST")).fetchall()
        activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name NULLS FIRST")).fetchall()
        cable_types = conn.execute(text("SELECT id, name FROM cable_type ORDER BY name NULLS FIRST")).fetchall()

    if not technicians:
        st.info("You don't have a team.")
        return

    loc_options = {loc.name: loc.id for loc in locations}
    act_options = {act.name: act.id for act in activities}
    cable_options = {ct.name: ct.id for ct in cable_types}
    cable_id_to_name = {ct.id: ct.name for ct in cable_types}
    tech_options = {tech.name: tech.id for tech in technicians}
    tech_ids = [tech.id for tech in technicians]

    latest_tasks = {}
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT technician_id, location_id, activity_id, cable_type_id, rack, quantity, percent
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

    df = pd.DataFrame([{
        "Technician": tech.name,
        "Location": next((loc.name for loc in locations if loc.id == latest_tasks.get(tech.id, {}).get("location_id")), list(loc_options.keys())[0]),
        "Activity": next((act.name for act in activities if act.id == latest_tasks.get(tech.id, {}).get("activity_id")), list(act_options.keys())[0]),
        "Cable Type": cable_id_to_name.get(latest_tasks.get(tech.id, {}).get("cable_type_id"), list(cable_options.keys())[0]),
        "Rack": latest_tasks.get(tech.id, {}).get("rack", ""),
        "Quantity": latest_tasks.get(tech.id, {}).get("quantity", 0),
        "Percent": latest_tasks.get(tech.id, {}).get("percent", 0)
    } for tech in technicians])

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        key="assignments_editor",
        column_config={
            "Location": st.column_config.SelectboxColumn("Location", options=list(loc_options.keys())),
            "Activity": st.column_config.SelectboxColumn("Activity", options=list(act_options.keys())),
            "Cable Type": st.column_config.SelectboxColumn("Cable Type", options=list(cable_options.keys())),
            "Rack": st.column_config.TextColumn("Rack", max_chars=5),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=0, step=1),
            "Percent": st.column_config.NumberColumn("Percent", min_value=0, max_value=100, step=1)
        }
    )

    if st.button("📂 Save tasks"):
        with engine.begin() as conn:
            for idx, row in edited_df.iterrows():
                original = df.iloc[idx]
                if (
                    row["Location"] == original["Location"] and
                    row["Activity"] == original["Activity"] and
                    row["Cable Type"] == original["Cable Type"] and
                    str(row["Rack"]).strip() == str(original["Rack"]).strip() and
                    int(row["Quantity"]) == int(original["Quantity"]) and
                    int(row["Percent"]) == int(original["Percent"])
                ):
                    continue

                tech_name = row["Technician"]
                tech_id = tech_options.get(tech_name)
                loc_id = loc_options.get(row["Location"])
                act_id = act_options.get(row["Activity"])
                cable_id = cable_options.get(row["Cable Type"])
                rack = str(row.get("Rack", "")).strip()[:5]
                quantity = max(0, int(row.get("Quantity", 0)))
                percent = min(100, max(0, int(row.get("Percent", 0))))

                if tech_id and loc_id:
                    if not act_id:
                        act_id = None
                    conn.execute(text("""
                        INSERT INTO technician_tasks (
                            technician_id, location_id, activity_id, cable_type_id, rack, source, timestamp, quantity, percent
                        )
                        VALUES (:tech_id, :loc_id, :act_id, :cable_type_id, :rack, :source, :timestamp, :quantity, :percent)
                    """), {
                        "tech_id": tech_id,
                        "loc_id": loc_id,
                        "act_id": act_id,
                        "cable_type_id": cable_id,
                        "rack": rack,
                        "source": team_lead_id,
                        "timestamp": datetime.now(),
                        "quantity": quantity,
                        "percent": percent
                    })

        st.success("✅ Changes saved!")
        st.rerun()
