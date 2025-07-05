from sqlalchemy import create_engine
import streamlit as st

def get_engine():
    db = st.secrets["database"]
    return create_engine(
        f"postgresql+psycopg2://{db.user}:{db.password}@{db.host}:{db.port}/{db.dbname}"
    )
