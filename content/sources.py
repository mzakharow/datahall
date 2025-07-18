import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime
from db import get_engine
from auth import is_admin
from zoneinfo import ZoneInfo

def run():
    st.title("📊 Sources")

    user = st.session_state.get("user")
    if not user or not is_admin(user):
        st.error("Access denied")
        return
