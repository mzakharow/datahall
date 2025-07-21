import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, time, timedelta
from db import get_engine
from auth import is_admin
from zoneinfo import ZoneInfo

def run():
    st.title("📊 Technician Tasks Report")

    user = st.session_state.get("user")
    if not user or not is_admin(user):
        st.error("Access denied")
        return

    engine = get_engine()

    LOCAL_TIMEZONE = "America/Chicago"
    now_local = datetime.now(ZoneInfo(LOCAL_TIMEZONE))
    today_local = now_local.date()

    selected_date = st.date_input("Select date", value=today_local)
    show_latest_only = st.checkbox("Show current tasks only (1 per tech)", value=True)

    start_datetime = datetime.combine(selected_date, time.min).replace(tzinfo=ZoneInfo(LOCAL_TIMEZONE))
    end_datetime = start_datetime + timedelta(days=1)

    with engine.connect() as conn:
        if show_latest_only:
            query = """
                SELECT 
                    tech.id AS technician_id,
                    tech.name AS technician,
                    COALESCE(tl.name, '—') AS team_lead,
                    loc.name AS location,
                    act.name AS activity,
                    ct.name AS cable_type,
                    r.name AS rack,
                    COALESCE(src.name, '—') AS created_by,
                    task.timestamp
                FROM technicians tech
                LEFT JOIN technicians tl ON tech.team_lead = tl.id
                LEFT JOIN (
                       SELECT *
                    FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (PARTITION BY technician_id ORDER BY timestamp DESC) AS rn
                        FROM technician_tasks
                        WHERE DATE(timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :selected_date
                    ) sub
                    WHERE rn = 1
                ) task ON task.technician_id = tech.id
                LEFT JOIN technicians src ON task.source = src.id
                LEFT JOIN locations loc ON task.location_id = loc.id
                LEFT JOIN activities act ON task.activity_id = act.id
                LEFT JOIN cable_type ct ON task.cable_type_id = ct.id
                LEFT JOIN racks r ON task.rack_id = r.id
                WHERE tech.activ = true
                ORDER BY tech.name
            """
        else:
            query = """
                SELECT 
                    t.name AS technician,
                    COALESCE(tl.name, '—') AS team_lead,
                    l.name AS location,
                    a.name AS activity,
                    ct.name AS cable_type,
                    r.name,
                    COALESCE(src.name, '—') AS created_by,
                    task.timestamp
                FROM technician_tasks task
                LEFT JOIN technicians t ON task.technician_id = t.id
                LEFT JOIN technicians tl ON t.team_lead = tl.id         
                LEFT JOIN technicians src ON task.source = src.id 
                LEFT JOIN locations l ON task.location_id = l.id
                LEFT JOIN activities a ON task.activity_id = a.id
                LEFT JOIN cable_type ct ON task.cable_type_id = ct.id
                LEFT JOIN racks r ON task.rack_id = r.id
                WHERE DATE(task.timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :selected_date
                ORDER BY task.timestamp DESC
            """

        rows = conn.execute(text(query), {
            "selected_date": selected_date
        }).fetchall()

    if not rows:
        st.info("No tasks found for the selected date.")
        return

    df = pd.DataFrame([dict(row._mapping) for row in rows])

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(ZoneInfo(LOCAL_TIMEZONE))

    with st.expander("🔍 Filters"):
        for col in ["technician", "team_lead", "location", "activity", "rack"]:
            if col in df.columns:
                options = df[col].dropna().unique().tolist()
                selected = st.multiselect(f"Filter by {col}", options, key=f"filter_{col}")
                if selected:
                    df = df[df[col].isin(selected)]

    st.dataframe(df, use_container_width=True)
    st.caption(f"Total records: {len(df)}")


    with engine.connect() as conn:
        dhs = conn.execute(text("SELECT DISTINCT dh FROM racks ORDER BY dh")).fetchall()
        dh_options = [row.dh for row in dhs if row.dh]

    selected_dh = st.selectbox("📍 Select Datahall (DH)", dh_options)

    if selected_dh:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    r.name AS rack_name,
                    r.dh,
                    r.su,
                    r.lu,
                    r.row,
                    rs.position,
                    a.name AS activity,
                    ct.name AS cable_type,
                    s.name AS status,
                    rs.quantity,
                    rs.percent,
                    t.name AS created_by,
                    rs.created_at,
    
                    (
                        SELECT STRING_AGG(tt_tech.name, ', ')
                        FROM technician_tasks tt
                        JOIN technicians tt_tech ON tt.technician_id = tt_tech.id
                        WHERE tt.rack_id = r.id
                          AND tt.activity_id = rs.activity_id
                          AND tt.cable_type_id = rs.cable_type_id
                    ) AS technicians

                FROM racks r
                LEFT JOIN (
                    SELECT DISTINCT ON (rack_id, position, activity_id, cable_type_id)
                           *
                    FROM rack_states
                    ORDER BY rack_id, position, activity_id, cable_type_id, status_id, created_at DESC
                ) rs ON rs.rack_id = r.id

                LEFT JOIN activities a ON rs.activity_id = a.id
                LEFT JOIN cable_type ct ON rs.cable_type_id = ct.id
                LEFT JOIN statuses s ON rs.status_id = s.id
                LEFT JOIN technicians t ON rs.created_by = t.id

                WHERE r.dh = :selected_dh
                ORDER BY r.name, rs.created_at DESC NULLS LAST;
            """), {"selected_dh": selected_dh})

            rows = result.fetchall()
            if rows:
                df = pd.DataFrame([dict(row._mapping) for row in rows])

                with st.expander("🔍 Filters"):
                    for col in ["rack_name", "su", "lu"]:
                        if col in df.columns:
                            options = df[col].dropna().unique().tolist()
                            selected = st.multiselect(f"Filter by {col}", options, key=f"filter_{col}")
                            if selected:
                                df = df[df[col].isin(selected)]

                st.dataframe(df, use_container_width=True)
            else:
                st.info("No data for selected DH.")

    # LOCAL_TIMEZONE = "America/Chicago"
    # today_local = datetime.now(ZoneInfo(LOCAL_TIMEZONE)).date()
    selected_date = st.date_input("📅 Select date", value=today_local)

    # engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                r.name AS rack_name,
                r.dh,
                rs.position,
                a.name AS activity,
                ct.name AS cable_type,
                s.name AS status,
                rs.quantity,
                rs.percent,
                tech.name AS technician,
                u.name AS created_by,
                rs.created_at
            FROM rack_states rs
            JOIN racks r ON r.id = rs.rack_id
            LEFT JOIN activities a ON a.id = rs.activity_id
            LEFT JOIN cable_type ct ON ct.id = rs.cable_type_id
            LEFT JOIN statuses s ON s.id = rs.status_id
            LEFT JOIN technician_tasks tt 
                ON tt.rack_id = rs.rack_id 
                AND tt.created_at AT TIME ZONE 'UTC' AT TIME ZONE :tz >= :start_datetime
                      AND tt.created_at AT TIME ZONE 'UTC' AT TIME ZONE :tz < :end_datetime
            LEFT JOIN technicians tech ON tech.id = tt.technician_id
            LEFT JOIN technicians u ON u.id = rs.created_by
            WHERE rs.created_at AT TIME ZONE 'UTC' AT TIME ZONE :tz >= :start_datetime
              AND rs.created_at AT TIME ZONE 'UTC' AT TIME ZONE :tz < :end_datetime
            ORDER BY rs.created_at DESC
        """), {
            "selected_date": selected_date,
            "tz": LOCAL_TIMEZONE,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime
        }).fetchall()

    if not rows:
        st.info("No records found for the selected date.")
        return

    df = pd.DataFrame([dict(row._mapping) for row in rows])

    with st.expander("🔍 Filters"):
        if "rack_name" in df.columns:
            rack_options = df["rack_name"].dropna().unique().tolist()
            selected_racks = st.multiselect("Filter by Rack", rack_options, key="filter_by_rack_name")
            if selected_racks:
                df = df[df["rack_name"].isin(selected_racks)]

        if "created_by" in df.columns:
            created_by_options = df["created_by"].dropna().unique().tolist()
            selected_creators = st.multiselect("Filter by Created By", created_by_options, key="filter_by_created_by")
            if selected_creators:
                df = df[df["created_by"].isin(selected_creators)]

    st.dataframe(df, use_container_width=True)
