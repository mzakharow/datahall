import streamlit as st
from sqlalchemy import text
from db import get_engine

def get_user_by_email(email):
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM technicians WHERE LOWER(email) = :email"),
            {"email": email.lower()}
        ).first()
        return dict(row._mapping) if row else None

def is_team_lead(user):
    return user and user.get("is_teamlead")

def is_admin(user):
    return user and user.get("admin")
