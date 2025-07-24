
         
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

        submitted = st.form_submit_button("✅ Add Rack")

    if submitted:
        if not name or not dh:
            st.error("Please fill in at least Rack Name and DH.")
            return

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO racks (name, dh, su, lu, row)
                VALUES (:name, :dh, :su, :lu, :row)
            """), {
                "name": name.strip(),
                "dh": dh.strip(),
                "su": su.strip() or None,
                "lu": lu.strip() or None,
                "row": row_value.strip() or None
            })

        st.success(f"✅ Rack '{name}' added.")
        st.rerun()


    with engine.connect() as conn:
        existing_racks = conn.execute(text("SELECT id, name, dh, su, lu, row FROM racks ORDER BY name")).fetchall()

    st.subheader("📋 Existing Racks")
    if existing_racks:
        st.table([dict(row._mapping) for row in existing_racks])
    else:
        st.info("No racks found.")
