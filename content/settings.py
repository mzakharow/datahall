from db import get_engine
import pandas as pd
import streamlit as st
from sqlalchemy import text
import re
from auth import encode_email, decode_email

def run():
    st.title("⚙️ Settings")

    col1, col2, col3 = st.columns(3)

    engine = get_engine()

    # ====== Locations ======
    with col1:
        st.subheader("📍 Locations")

        with engine.connect() as conn:
            df_loc = pd.read_sql("SELECT id, name FROM locations ORDER BY id", conn)

        edited_df = st.data_editor(
            df_loc.copy(),
            num_rows="dynamic",
            use_container_width=True,
            key="locations_editor"
        )

        if st.button("💾 Save locations"):
            seen = set()
            error = False

            with engine.begin() as conn:
                new_ids = []

                for i, row in edited_df.iterrows():
                    name = str(row["name"]).strip()
                    if not name:
                        continue
                    lname = name.lower()
                    if lname in seen:
                        st.warning(f"Duplicate location: {name}")
                        error = True
                        continue
                    seen.add(lname)

                    if i < len(df_loc):
                        id_ = int(df_loc.iloc[i]["id"])
                        new_ids.append(id_)
                        # Update
                        conn.execute(text("UPDATE locations SET name = :name WHERE id = :id"),
                                     {"name": name, "id": id_})
                    else:
                        # Insert
                        result = conn.execute(text("INSERT INTO locations (name) VALUES (:name) RETURNING id"), {"name": name})
                        new_id = result.scalar()
                        new_ids.append(new_id)

                # Delete removed
                old_ids = set(df_loc["id"])
                deleted_ids = old_ids - set(new_ids)
                for del_id in deleted_ids:
                    conn.execute(text("DELETE FROM technician_tasks WHERE location_id = :id"), {"id": del_id})
                    conn.execute(text("DELETE FROM locations WHERE id = :id"), {"id": del_id})

            if not error:
                st.success("✅ Locations saved")
                st.rerun()

    # ====== Activities ======
    with col2:
        st.subheader("⚙️ Activities")

        with engine.connect() as conn:
            df_act = pd.read_sql("SELECT id, name FROM activities ORDER BY id", conn)

        edited_df = st.data_editor(
            df_act.copy(),
            num_rows="dynamic",
            use_container_width=True,
            key="activities_editor"
        )

        if st.button("💾 Save activities"):
            seen = set()
            error = False

            with engine.begin() as conn:
                new_ids = []

                for i, row in edited_df.iterrows():
                    name = str(row["name"]).strip()
                    if not name:
                        continue
                    lname = name.lower()
                    if lname in seen:
                        st.warning(f"Duplicate activity: {name}")
                        error = True
                        continue
                    seen.add(lname)

                    if i < len(df_act):
                        id_ = int(df_act.iloc[i]["id"])
                        new_ids.append(id_)
                        # Update
                        conn.execute(text("UPDATE activities SET name = :name WHERE id = :id"),
                                     {"name": name, "id": id_})
                    else:
                        # Insert
                        result = conn.execute(text("INSERT INTO activities (name) VALUES (:name) RETURNING id"), {"name": name})
                        new_id = result.scalar()
                        new_ids.append(new_id)

                # Delete removed
                old_ids = set(df_act["id"])
                deleted_ids = old_ids - set(new_ids)
                for del_id in deleted_ids:
                    conn.execute(text("DELETE FROM technician_tasks WHERE activity_id = :id"), {"id": del_id})
                    conn.execute(text("DELETE FROM activities WHERE id = :id"), {"id": del_id})

            if not error:
                st.success("✅ Activities saved")
                st.rerun()
    with col3:
        st.subheader("🔌 Cable Types")

        with engine.connect() as conn:
            df_cable = pd.read_sql("SELECT id, name FROM cable_type ORDER BY id", conn)

        edited_df = st.data_editor(
            df_cable.copy(),
            num_rows="dynamic",
            use_container_width=True,
            key="cable_editor"
        )

        if st.button("💾 Save cable types"):
            seen = set()
            error = False

            with engine.begin() as conn:
                new_ids = []

                for i, row in edited_df.iterrows():
                    name = str(row["name"]).strip()
                    if not name:
                        continue
                    lname = name.lower()
                    if lname in seen:
                        st.warning(f"Duplicate cable type: {name}")
                        error = True
                        continue
                    seen.add(lname)

                    if i < len(df_cable):
                        id_ = int(df_cable.iloc[i]["id"])
                        new_ids.append(id_)
                        # Update
                        conn.execute(text("UPDATE cable_type SET name = :name WHERE id = :id"),
                                     {"name": name, "id": id_})
                    else:
                        # Insert
                        result = conn.execute(
                            text("INSERT INTO cable_type (name) VALUES (:name) RETURNING id"),
                            {"name": name}
                        )
                        new_id = result.scalar()
                        new_ids.append(new_id)

                # Delete removed cable types
                old_ids = set(df_cable["id"])
                deleted_ids = old_ids - set(new_ids)
                for del_id in deleted_ids:
                    conn.execute(text("DELETE FROM technician_tasks WHERE cable_type_id = :id"), {"id": del_id})
                    conn.execute(text("DELETE FROM cable_type WHERE id = :id"), {"id": del_id})

            if not error:
                st.success("✅ Cable types saved")
                st.rerun()
            
    # ====== Technicians ======
    st.subheader("👷 Technicians")

    with engine.connect() as conn:
        df_tech = pd.read_sql("SELECT * FROM technicians ORDER BY id", conn)

    all_names = {row["id"]: row["name"] for _, row in df_tech.iterrows()}
    team_leads = {row["id"]: row["name"] for _, row in df_tech.iterrows() if row.get("is_teamlead")}

    tech_display = df_tech[["id", "name", "email", "team_lead", "activ", "is_teamlead", "admin"]].copy()
    tech_display["del"] = False
    tech_display["team_lead_name"] = tech_display["team_lead"].map(team_leads).fillna("—")

    team_lead_names = list(team_leads.values())
    team_lead_names.insert(0, "—")
    # df_tech["encoded_email"] = encode_email(df_tech["email"])

    edited = st.data_editor(
        tech_display[["name", "email", "team_lead_name", "is_teamlead", "activ", "admin", "del"]],
        num_rows="dynamic",
        use_container_width=True,
        key="technicians_editor",
        column_config={
            "team_lead_name": st.column_config.SelectboxColumn(
                label="Team Lead",
                options=team_lead_names,
                required=False
            ),
            "is_teamlead": st.column_config.CheckboxColumn("is teamlead"),
            "activ": st.column_config.CheckboxColumn("active"),
            # "encoded_email": st.column_config.TextColumn("Encoded Email", disabled=True),
            "del": st.column_config.CheckboxColumn("del")
        }
    )

    if st.button("💾 Save technicians"):
        emails_seen = set()
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        error = False

        with engine.begin() as conn:
            for idx, row in edited.iterrows():
                name = str(row["name"]).strip()
                email = str(row["email"]).strip().lower()
                team_lead_name = str(row["team_lead_name"]).strip()
                is_teamlead = bool(row["is_teamlead"])
                activ = bool(row["activ"])
                admin = bool(row["admin"])
                to_delete = row["del"]

                team_lead_id = None
                for tid, tname in team_leads.items():
                    if tname == team_lead_name:
                        team_lead_id = tid
                        break

                if not name and not email:
                    continue

                if not name or not email:
                    st.warning(f"Row {idx + 1}: name and email")
                    error = True
                    continue

                if not re.match(email_regex, email):
                    st.warning(f"Row {idx + 1}: wrong email: '{email}'")
                    error = True
                    continue

                if email in emails_seen:
                    st.warning(f"Row {idx + 1}: email '{email}' already exist.")
                    error = True
                    continue

                emails_seen.add(email)

                if idx >= len(df_tech):
                    if not to_delete:
                        conn.execute(text("""
                            INSERT INTO technicians (name, email, team_lead, is_teamlead, activ, admin)
                            VALUES (:name, :email, :team_lead, :is_teamlead, :activ, :admin)
                        """), {
                            "name": name, "email": email,
                            "team_lead": team_lead_id, "is_teamlead": is_teamlead, "activ": activ, "admin": admin,
                        })
                else:
                    tech_id = df_tech.iloc[idx]["id"]
                    if to_delete:
                        conn.execute(text("DELETE FROM technician_tasks WHERE technician_id = :id"), {"id": int(tech_id)})
                        conn.execute(text("DELETE FROM technicians WHERE id = :id"), {"id": int(tech_id)})
                    else:
                        conn.execute(text("""
                            UPDATE technicians
                            SET name = :name,
                                email = :email,
                                team_lead = :team_lead,
                                is_teamlead = :is_teamlead,
                                activ = :activ,
                                admin = :admin
                            WHERE id = :id
                        """), {
                            "name": name, "email": email,
                            "team_lead": int(team_lead_id) if team_lead_id is not None else None,
                            "is_teamlead": is_teamlead,
                            "activ": activ,
                            "admin": admin,
                            "id": int(tech_id)
                        })

        if not error:
            st.success("Updated")
            st.rerun()


    st.subheader("📂 Manage Projects")
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT project, time_zone, customer FROM projects ORDER BY project")).fetchall()
        df = pd.DataFrame([dict(row._mapping) for row in rows]) if rows else pd.DataFrame(
            columns=["project", "time_zone", "customer"]
        )

    st.write("### 📝 Existing Projects")
    
    with st.form("edit_projects_form"):
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="projects_editor",
            column_config={
                "project": st.column_config.TextColumn("Project ID", help="Unique ID (letters, digits, '-')"),
                "time_zone": st.column_config.TextColumn("Time Zone", help="e.g., America/Chicago"),
                "customer": st.column_config.TextColumn("Customer", help="Max 20 chars")
            }
        )
        submitted = st.form_submit_button("💾 Save Changes")

    if submitted:
        with engine.begin() as conn:
            for _, row in edited_df.iterrows():
                if pd.notna(row["project"]) and pd.notna(row["time_zone"]):
                    existing = conn.execute(text("""
                        SELECT 1 FROM projects WHERE project = :project
                    """), {"project": str(row["project"]).strip()}).fetchone()

                    if existing:
                        conn.execute(text("""
                            UPDATE projects
                            SET time_zone = :time_zone, customer = :customer
                            WHERE project = :project
                        """), {
                            "project": str(row["project"]).strip(),
                            "time_zone": str(row["time_zone"]).strip(),
                            "customer": str(row["customer"]).strip() if pd.notna(row["customer"]) else None
                        })
                    else:
                        conn.execute(text("""
                            INSERT INTO projects (project, time_zone, customer)
                            VALUES (:project, :time_zone, :customer)
                        """), {
                            "project": str(row["project"]).strip(),
                            "time_zone": str(row["time_zone"]).strip(),
                            "customer": str(row["customer"]).strip() if pd.notna(row["customer"]) else None
                        })

        st.success("✅ Projects updated successfully!")
        st.rerun()