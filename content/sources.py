
         
import streamlit as st
from sqlalchemy import text
from db import get_engine

def run():
    st.title("📦 Sources")

    engine = get_engine()


    st.markdown("---")
    st.subheader("➕ Add New Rack")

    with st.form("add_rack_form"):
        name = st.text_input("Rack Name", max_chars=50)
        dh = st.text_input("Datahall (DH)", max_chars=15)
        su = st.text_input("SU", max_chars=10)
        lu = st.text_input("LU", max_chars=10)
        row_value = st.text_input("Row", max_chars=10)

        activity = st.selectbox("Activity", activity_options)  # заранее загрузи из БД
        position = st.selectbox("Position", ["left", "right", "varies"])
        cable_type = st.selectbox("Cable Type", cable_type_options)  # из БД
        quantity = st.number_input("Quantity", min_value=0)
        measurement = st.text_input("Measurement (optional)", max_chars=20)

        submitted = st.form_submit_button("✅ Add Rack")

    if submitted:
        if not name or not dh:
            st.error("Please fill in at least Rack Name and DH.")
            st.stop()

        with engine.begin() as conn:
        # Check if rack already exists
            existing = conn.execute(text("""
                SELECT id FROM racks WHERE name = :name AND dh = :dh
            """), {"name": name.strip(), "dh": dh.strip()}).fetchone()

            if existing:
            # Update existing rack
                rack_id = existing.id
                conn.execute(text("""
                    UPDATE racks
                    SET su = :su, lu = :lu, row = :row
                    WHERE id = :rack_id
                """), {
                    "su": su.strip() or None,
                    "lu": lu.strip() or None,
                    "row": row_value.strip() or None,
                    "rack_id": rack_id
                })
                st.info(f"ℹ️ Rack '{name}' updated.")
            else:
            # Insert new rack
                result = conn.execute(text("""
                    INSERT INTO racks (name, dh, su, lu, row)
                    VALUES (:name, :dh, :su, :lu, :row)
                    RETURNING id
                """), {
                    "name": name.strip(),
                    "dh": dh.strip(),
                    "su": su.strip() or None,
                    "lu": lu.strip() or None,
                    "row": row_value.strip() or None
                })
                rack_id = result.scalar()
                st.success(f"✅ Rack '{name}' added.")

        # Insert into rack_results only if required fields are filled
            if activity and position and cable_type and quantity > 0:
                conn.execute(text("""
                    INSERT INTO rack_results (rack_id, activity_id, position, cable_type_id, quantity, measurement)
                    VALUES (:rack_id, :activity, :position, :cable_type, :quantity, :measurement)
                """), {
                    "rack_id": rack_id,
                    "activity": activity,
                    "position": position,
                    "cable_type": cable_type,
                    "quantity": quantity,
                    "measurement": measurement.strip() or None
                })
                st.success("✅ rack_results record added.")
            else:
                st.warning("⚠️ rack_results not added. Make sure activity, position, cable_type and quantity are filled.")
    
        st.rerun()


    with engine.connect() as conn:
        existing_racks = conn.execute(text("SELECT id, name, dh, su, lu, row FROM racks ORDER BY name")).fetchall()

    st.subheader("📋 Existing Racks")
    if existing_racks:
        st.table([dict(row._mapping) for row in existing_racks])
    else:
        st.info("No racks found.")
