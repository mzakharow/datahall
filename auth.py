# import streamlit as st
# from sqlalchemy import text
# from db import get_engine

# def get_user_by_email(email):
#     engine = get_engine()
#     with engine.connect() as conn:
#         row = conn.execute(
#             text("SELECT * FROM technicians WHERE LOWER(email) = :email"),
#             {"email": email.lower()}
#         ).first()
#         return dict(row._mapping) if row else None

# def is_team_lead(user):
#     return user and user.get("is_teamlead")

# def is_admin(user):
#     return user and user.get("admin")

from sqlalchemy import create_engine, text
import streamlit as st

db = st.secrets["database"]
engine = create_engine(
    f"postgresql+psycopg2://{db.user}:{db.password}@{db.host}:{db.port}/{db.dbname}"
)

def get_user_by_email(email):
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM technicians WHERE email = :email"), {"email": email}).first()
        return dict(row._mapping) if row else None

def register_user(name, email):
    with engine.begin() as conn:
        exists = conn.execute(text("SELECT 1 FROM technicians WHERE email = :email"), {"email": email}).first()
        if exists:
            return False
        conn.execute(text("INSERT INTO technicians (name, email) VALUES (:name, :email)"), {"name": name, "email": email})
        return True

def is_team_lead(user):
    return user.get("is_teamlead", False)

def is_admin(user):
    return user.get("admin", False)
