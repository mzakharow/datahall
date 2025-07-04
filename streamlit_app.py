import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
import re

st.set_page_config(
    page_title="Survey",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
# st.markdown(hide_streamlit_style, unsafe_allow_html=True)

db = st.secrets["database"]
engine = create_engine(
    f"postgresql+psycopg2://{db.user}:{db.password}@{db.host}:{db.port}/{db.dbname}"
)

if "email_checked" not in st.session_state:
    st.session_state.email_checked = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# ======================= Pages ==========================

def user_survey_page():
    st.title("📋 Опрос сотрудника")

    # --- State
    if "email_checked" not in st.session_state:
        st.session_state.email_checked = False
    if "user_data" not in st.session_state:
        st.session_state.user_data = None

    # --- Email from query params
    query_params = st.query_params
    # email_param = query_params.get("email", "")
    
    if "email" not in st.session_state:
        st.session_state.email = query_params.get("email", "")

    email = st.text_input("Введите ваш email", value=st.session_state.email)
    st.session_state.email = email  
    # email = st.text_input("Введите ваш email", value=email_param)

    # --- Проверка email
    if st.button("Check email"):
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM technicians WHERE LOWER(email) = :email"),
                {"email": email.lower()}
            ).first()

        if row:
            st.session_state.email_checked = True
            st.session_state.user_data = dict(row._mapping)
            st.success("Email success!")
        else:
            st.error("Email doesn't exist")

    # --- Main form
    if st.session_state.email_checked:
        user = st.session_state.user_data

        with engine.connect() as conn:
            locations = conn.execute(text("SELECT id, name FROM locations ORDER BY name")).fetchall()
            activities = conn.execute(text("SELECT id, name FROM activities ORDER BY name")).fetchall()

        loc_options = {loc.name: loc.id for loc in locations}
        act_options = {act.name: act.id for act in activities}

        selected_location = st.selectbox("Выберите локацию", list(loc_options.keys()))
        selected_activity = st.selectbox("Выберите активность", list(act_options.keys()))

        if st.button("Отправить ответ"):
            response = {
                "email": user["email"],
                "technician_id": user["id"],
                "location_id": loc_options[selected_location],
                "activity_id": act_options[selected_activity],
                "timestamp": datetime.now()
            }

            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO technician_responses (technician_id, location_id, activity_id, timestamp)
                    VALUES (:technician_id, :location_id, :activity_id, :timestamp)
                """), response)

            st.success("Ответ сохранён!")
            st.json(response)  # del

def settings_page():
    st.title("⚙️ Настройки")

    col1, col2 = st.columns(2)

    # ====== Locations ======
    with col1:
        st.subheader("📍 Locations")

        with engine.connect() as conn:
            df_loc = pd.read_sql("SELECT id, name FROM locations ORDER BY id", conn)

        edited_df = st.data_editor(
            df_loc[["name"]],
            num_rows="dynamic",
            use_container_width=True,
            key="locations_editor"
        )

        if st.button("💾 Save locations"):
            names_seen = set()
            duplicate_found = False

            for _, row in edited_df.iterrows():
                name = str(row["name"]).strip().lower()
                if name in names_seen:
                    duplicate_found = True
                    break
                if name:
                    names_seen.add(name)

            if duplicate_found:
                st.error("❌ location isn't unique.")
            else:
                with engine.begin() as conn:
                    for idx, row in edited_df.iterrows():
                        name = str(row["name"]).strip()
                        if not name:
                            continue
                        if idx < len(df_loc):
                            id_ = int(df_loc.iloc[idx]["id"])
                            conn.execute(
                                text("UPDATE locations SET name = :name WHERE id = :id"),
                                {"name": name, "id": id_}
                            )
                        else:
                            conn.execute(
                                text("INSERT INTO locations (name) VALUES (:name)"),
                                {"name": name}
                            )
                st.success("Done")
                st.rerun()

    # ====== АКТИВНОСТИ ======
    with col2:
        st.subheader("Activities")

        with engine.connect() as conn:
            df_act = pd.read_sql("SELECT id, name FROM activities ORDER BY id", conn)

        edited_act = st.data_editor(
            df_act[["name"]],
            num_rows="dynamic",
            use_container_width=True,
            key="activities_editor"
        )

        if st.button("💾 Save activities"):
            names_seen = set()
            duplicate_found = False

            for _, row in edited_act.iterrows():
                name = str(row["name"]).strip().lower()
                if name in names_seen:
                    duplicate_found = True
                    break
                if name:
                    names_seen.add(name)

            if duplicate_found:
                st.error("❌ activitie isn't unique")
            else:
                with engine.begin() as conn:
                    for idx, row in edited_act.iterrows():
                        name = str(row["name"]).strip()
                        if not name:
                            continue
                        if idx < len(df_act):
                            id_ = int(df_act.iloc[idx]["id"])
                            conn.execute(
                                text("UPDATE activities SET name = :name WHERE id = :id"),
                                {"name": name, "id": id_}
                            )
                        else:
                            conn.execute(
                                text("INSERT INTO activities (name) VALUES (:name)"),
                                {"name": name}
                            )
                st.success("Активности сохранены")
                st.rerun()

    # ====== ТЕХНИКИ ======
    st.subheader("👷 Technicians")

    with engine.connect() as conn:
        df_tech = pd.read_sql("SELECT * FROM technicians ORDER BY id", conn)

    # Словари ID → имя
    all_names = {row["id"]: row["name"] for _, row in df_tech.iterrows()}
    team_leads = {row["id"]: row["name"] for _, row in df_tech.iterrows() if row.get("is_teamlead")}

    tech_display = df_tech[["id", "name", "email", "team_lead", "activ", "is_teamlead"]].copy()
    tech_display["del"] = False
    tech_display["team_lead_name"] = tech_display["team_lead"].map(team_leads).fillna("—")

    team_lead_names = list(team_leads.values())
    team_lead_names.insert(0, "—")

    edited = st.data_editor(
        tech_display[["name", "email", "team_lead_name", "is_teamlead", "activ", "Удалить"]],
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
            "Удалить": st.column_config.CheckboxColumn("Del")
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
                to_delete = row["Удалить"]

                team_lead_id = None
                for tid, tname in team_leads.items():
                    if tname == team_lead_name:
                        team_lead_id = tid
                        break

                if not name and not email:
                    continue

                if not name or not email:
                    st.warning(f"Строка {idx + 1}: name and email")
                    error = True
                    continue

                if not re.match(email_regex, email):
                    st.warning(f"Строка {idx + 1}: wrong email: '{email}'")
                    error = True
                    continue

                if email in emails_seen:
                    st.warning(f"Строка {idx + 1}: email '{email}' already exist.")
                    error = True
                    continue

                emails_seen.add(email)

                if idx >= len(df_tech):
                    if not to_delete:
                        conn.execute(text("""
                            INSERT INTO technicians (name, email, team_lead, is_teamlead, activ)
                            VALUES (:name, :email, :team_lead, :is_teamlead, :activ)
                        """), {
                            "name": name, "email": email,
                            "team_lead": team_lead_id, "is_teamlead": is_teamlead, "activ": activ
                        })
                else:
                    tech_id = df_tech.iloc[idx]["id"]
                    if to_delete:
                        conn.execute(text("DELETE FROM technicians WHERE id = :id"), {"id": int(tech_id)})
                    else:
                        conn.execute(text("""
                            UPDATE technicians
                            SET name = :name,
                                email = :email,
                                team_lead = :team_lead,
                                is_teamlead = :is_teamlead,
                                activ = :activ
                            WHERE id = :id
                        """), {
                            "name": name, "email": email,
                            "team_lead": int(team_lead_id) if team_lead_id is not None else None,
                            "is_teamlead": is_teamlead,
                            "activ": activ,
                            "id": int(tech_id)
                        })

        if not error:
            st.success("Сотрудники обновлены")
            st.rerun()

# ======================= Навигация ==========================

st.sidebar.title("Menu")
page = st.sidebar.radio("Pages", ["Survey", "Settings"])

if page == "Survey":
    user_survey_page()
elif page == "Settings":
    settings_page()
