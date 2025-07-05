from db import get_engine
import pandas as pd
import streamlit as st
from sqlalchemy import text
import re

def run():
    st.title("⚙️ Settings")
