import bcrypt
from sqlalchemy import create_engine, text
import streamlit as st

# Настройки подключения к БД
db = st.secrets["database"]
engine = create_engine(
    f"postgresql+psycopg2://{db.user}:{db.password}@{db.host}:{db.port}/{db.dbname}"
)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def get_user_by_email(email: str) -> dict | None:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM technicians WHERE LOWER(email) = :email"),
            {"email": email.lower()}
        ).first()

        if result:
            return dict(result._mapping)
        return None

def register_user(name: str, email: str, password: str) -> bool:
    if get_user_by_email(email):
        return False  # Email уже существует

    hashed_pw = hash_password(password)
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO technicians (name, email, password, is_teamlead, activ, admin)
                VALUES (:name, :email, :password, false, true, false)
            """),
            {"name": name, "email": email.lower(), "password": password}
        )
    return True

def is_team_lead(user: dict) -> bool:
    return user.get("is_teamlead", False)

def is_admin(user: dict) -> bool:
    return user.get("admin", False)
