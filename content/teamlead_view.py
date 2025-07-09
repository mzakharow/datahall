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

    with st.form("task_form"):
        st.subheader("📋 Assign Tasks")
        task_entries = []

        for tech in technicians:
            st.markdown(f"### 👷 {tech.name}")
            loc = st.selectbox(f"📍 Location", list(loc_options.keys()), key=f"loc_{tech.id}")
            acts = st.multiselect(f"⚙️ Activities", list(act_options.keys()), key=f"acts_{tech.id}")
            cables = st.multiselect(f"🔌 Cable Types", list(cable_options.keys()), key=f"cables_{tech.id}")
            rack = st.text_input("Rack", key=f"rack_{tech.id}").strip()[:5]

            task_entries.append({
                "technician_id": tech.id,
                "location": loc,
                "activities": acts,
                "cables": cables,
                "rack": rack
            })

        submitted = st.form_submit_button("💾 Save tasks")

    if submitted:
        now = datetime.now()
        with engine.begin() as conn:
            for entry in task_entries:
                tech_id = entry["technician_id"]
                loc_id = loc_options.get(entry["location"])
                rack = entry["rack"]

                for act_name in entry["activities"]:
                    act_id = act_options.get(act_name)
                    for cable_name in entry["cables"]:
                        cable_id = cable_options.get(cable_name)
                        conn.execute(text("""
                            INSERT INTO technician_tasks (
                                technician_id, location_id, activity_id, cable_type_id, rack, source, timestamp
                            ) VALUES (
                                :tech_id, :loc_id, :act_id, :cable_id, :rack, :source, :timestamp
                            )
                        """), {
                            "tech_id": tech_id,
                            "loc_id": loc_id,
                            "act_id": act_id,
                            "cable_id": cable_id,
                            "rack": rack,
                            "source": team_lead_id,
                            "timestamp": now
                        })

        st.success("✅ Tasks saved!")
        st.rerun()
