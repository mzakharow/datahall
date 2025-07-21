from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from sqlalchemy import text
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

    positions = {"Varies": "varies", "Left": "left", "Right": "right"}
    
    with engine.connect() as conn:
        if show_all:
            technicians = conn.execute(text("""
                SELECT t1.id, t1.name, t2.name AS team_lead_name
                FROM technicians t1
                LEFT JOIN technicians t2 ON t1.team_lead = t2.id
                WHERE t1.activ = true
                ORDER BY t1.name
            """)).fetchall()
        else:
            technicians = conn.execute(text("""
                SELECT t1.id, t1.name, t2.name AS team_lead_name
                FROM technicians t1
                LEFT JOIN technicians t2 ON t1.team_lead = t2.id
                WHERE t1.team_lead = :tl_id AND t1.activ = true
                ORDER BY t1.name
            """), {"tl_id": team_lead_id}).fetchall()

        locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name NULLS FIRST")).fetchall()
        activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name NULLS FIRST")).fetchall()
        cable_types = conn.execute(text("SELECT id, name FROM cable_type ORDER BY name NULLS FIRST")).fetchall()
        # racks = conn.execute(text("SELECT id, name FROM raks ORDER BY name NULLS FIRST")).fetchall()
        # team_leads = conn.execute(text("SELECT id, name FROM technicians WHERE is_teamlead = True")).fetchone()
        racks = conn.execute(text("SELECT id, name, dh FROM racks ORDER BY name NULLS FIRST")).fetchall()

        tech_options = {tech.name: tech.id for tech in technicians}
        tech_ids = [tech.id for tech in technicians]
        tech_id_to_teamlead = {tech.id: tech.team_lead_name for tech in technicians}
        # team_lead_name = result.name if result else "-"

    if not technicians:
        st.info("You don't have a team.")
        return

    loc_options = {loc.name: loc.id for loc in locations}
    act_options = {act.name: act.id for act in activities}
    cable_options = {ct.name: ct.id for ct in cable_types}
    cable_id_to_name = {ct.id: ct.name for ct in cable_types}
    # tech_options = {tech.name: tech.id for tech in technicians}
    # tech_ids = [tech.id for tech in technicians]
    racks_options = {f"{rack.name} ({rack.dh})": rack.id for rack in racks}

    tech_options = {tech.name: tech.id for tech in technicians}
    tech_ids = [tech.id for tech in technicians]
    tech_id_to_teamlead = {tech.id: tech.team_lead_name for tech in technicians}

    LOCAL_TIMEZONE = "America/Chicago"
    today_local = datetime.now(ZoneInfo(LOCAL_TIMEZONE)).date()

    latest_tasks = {}
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT sub.technician_id, sub.location_id, sub.activity_id, sub.cable_type_id, sub.rack_id, sub.position, sub.timestamp, u.name AS created_by
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY technician_id ORDER BY timestamp DESC) as rn
                FROM technician_tasks
                WHERE technician_id = ANY(:tech_ids)
                  AND DATE(timestamp AT TIME ZONE 'UTC' AT TIME ZONE :tz) = :today
            ) sub
            LEFT JOIN technicians u ON u.id = sub.source
            WHERE rn = 1"""), {
            "tech_ids": tech_ids,
            "today": today_local,
            "tz": LOCAL_TIMEZONE
        }).fetchall()

        for row in rows:
            latest_tasks[row.technician_id] = dict(row._mapping)

    df = pd.DataFrame([{
        "#": i + 1,
        "Technician": tech.name,
        "Location": next((loc.name for loc in locations if loc.id == latest_tasks.get(tech.id, {}).get("location_id")), list(loc_options.keys())[0]),
        "Activity": next((act.name for act in activities if act.id == latest_tasks.get(tech.id, {}).get("activity_id")), list(act_options.keys())[0]),
        "Cable Type": cable_id_to_name.get(latest_tasks.get(tech.id, {}).get("cable_type_id"), list(cable_options.keys())[0]),
        # "Rack": next((rack.name for rack in racks if rack.id == latest_tasks.get(tech.id, {}).get("rack_id")), "-"),
        "Rack": next((f"{rack.name} ({rack.dh})" for rack in racks if rack.id == latest_tasks.get(tech.id, {}).get("rack_id")), "-"),
        "Position": latest_tasks.get(tech.id, {}).get("position", "Varies"),
        "Team lead": tech_id_to_teamlead.get(tech.id, "-"),
        "Created by": latest_tasks.get(tech.id, {}).get("created_by", "-"),
        # "Team lead": next((team_lead.name for team_lead in team_leads if team_lead.id == technicians.get(tech.id, {}).get("technician_id")), list(tech_ids.keys())[0]),
        # "Quantity": latest_tasks.get(tech.id, {}).get("quantity", 0),
        # "Percent": latest_tasks.get(tech.id, {}).get("percent", 0),
        "Time": latest_tasks.get(tech.id, {}).get("timestamp", "").astimezone(ZoneInfo(LOCAL_TIMEZONE)).strftime("%H:%M") if latest_tasks.get(tech.id, {}).get("timestamp") else ""
    } for i, tech in enumerate(technicians)])

    with st.form("edit_tasks_form"):
        edited_df = st.data_editor(
            df,
            num_rows="fixed",
            use_container_width=True,
            hide_index=True,
            key="assignments_editor",
            column_config={
                "#": st.column_config.NumberColumn("#", disabled=True),
                "Time": st.column_config.TextColumn("Time", disabled=True),
                "Location": st.column_config.SelectboxColumn("Location", options=list(loc_options.keys())),
                "Activity": st.column_config.SelectboxColumn("Activity", options=list(act_options.keys())),
                "Cable Type": st.column_config.SelectboxColumn("Cable Type", options=list(cable_options.keys())),
                "Rack": st.column_config.SelectboxColumn("Rack", options=list(racks_options.keys())),
                "Position": st.column_config.SelectboxColumn("Position", options=list(positions.keys())),
                # "Team lead": st.column_config.SelectboxColumn("Team lead", options=list(team_leads.keys())),
                # "Quantity": st.column_config.NumberColumn("Quantity", min_value=0, step=1, default=0),
                # "Percent": st.column_config.NumberColumn("Percent", min_value=0, max_value=100, step=1, default=0)
            }
        )
        submitted = st.form_submit_button("📂 Save tasks")

    # if st.button("📂 Save tasks"):
    if submitted:
        with engine.begin() as conn:
            for idx, row in edited_df.iterrows():
                original = df.iloc[idx]
                if (
                    row["Location"] == original["Location"] and
                    row["Activity"] == original["Activity"] and
                    row["Cable Type"] == original["Cable Type"] and
                    row["Rack"] == original["Rack"]
                    and row["Position"] == original["Position"]
                    # and int(row["Quantity"] if pd.notna(row["Quantity"]) else 0) == int(original["Quantity"] if pd.notna(original["Quantity"]) else 0) and
                    # int(row["Percent"] if pd.notna(row["Percent"]) else 0) == int(original["Percent"] if pd.notna(original["Percent"]) else 0)
                ):
                    continue

                tech_name = row["Technician"]
                tech_id = tech_options.get(tech_name)
                loc_id = loc_options.get(row["Location"])
                act_id = act_options.get(row["Activity"])
                cable_id = cable_options.get(row["Cable Type"])
                rack_id = racks_options.get(row["Rack"])
                position = row.get("Position")
                # quantity = max(0, int(row.get("Quantity", 0)))
                # percent = min(100, max(0, int(row.get("Percent", 0))))

                if tech_id and loc_id:
                    if not act_id:
                        act_id = None
                    conn.execute(text("""
                        INSERT INTO technician_tasks (
                            technician_id, location_id, activity_id, cable_type_id, rack_id, source, position, timestamp
                        )
                        VALUES (:tech_id, :loc_id, :act_id, :cable_type_id, :rack_id, :source, :position, :timestamp)
                    """), {
                        "tech_id": tech_id,
                        "loc_id": loc_id,
                        "act_id": act_id,
                        "cable_type_id": cable_id,
                        "rack_id": rack_id,
                        "source": team_lead_id,
                        "position": position,
                        "timestamp": datetime.now()
                        # "quantity": quantity,
                        # "percent": percent
                    })

        st.success("✅ Changes saved!")
        st.rerun()
    
    st.markdown("---")
    st.subheader("📌 Close task")

    with engine.connect() as conn:
        racks = conn.execute(text("SELECT id, name, dh FROM racks ORDER BY name")).fetchall()
        activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name")).fetchall()
        cable_types = conn.execute(text("SELECT id, name FROM cable_type ORDER BY name")).fetchall()
        statuses = conn.execute(text("SELECT id, name FROM statuses ORDER BY name")).fetchall()

    rack_options = {f"{r.name} ({r.dh})": r.id for r in racks}
    activity_options = {a.name: a.id for a in activities}
    cable_type_options = {c.name: c.id for c in cable_types}
    status_options = {s.name: s.id for s in statuses}
    positions = {"Varies": "varies", "Left": "left", "Right": "right"}

    with st.form("rack_task_form"):
        col1, col2 = st.columns(2)
        with col1:
            selected_rack = st.selectbox("Rack", list(rack_options.keys()))
            selected_activity = st.selectbox("Activity", list(activity_options.keys()))
            selected_cable = st.selectbox("Cable type", list(cable_type_options.keys()))
            selected_status = st.selectbox("Status", list(status_options.keys()))
        with col2:
            selected_position = st.selectbox("position", list(positions.keys()))
            quantity = st.number_input("quantity", min_value=0, step=1)
            percent = st.slider("percent", min_value=0, max_value=100, step=1)

        submitted = st.form_submit_button("✅ Save")

    if submitted:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO rack_states (rack_id, activity_id, cable_type_id, status_id, position, quantity, percent, created_by, created_at)
                VALUES (:rack_id, :activity_id, :cable_type_id, :status_id, :position, :quantity, :percent, :created_by, NOW())
            """), {
                "rack_id": rack_options[selected_rack],
                "activity_id": activity_options[selected_activity],
                "cable_type_id": cable_type_options[selected_cable],
                "status_id": status_options[selected_status],
                "position": positions[selected_position],
                "quantity": quantity,
                "percent": percent,
                "created_by": st.session_state.user["id"]
            })
        st.success("✅ Changes saved!")
