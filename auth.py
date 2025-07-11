import bcrypt
from sqlalchemy import create_engine, text
import streamlit as st
import base64
from db import get_engine
import secrets
from datetime import datetime
from typing import Optional

db = st.secrets["database"]
engine = get_engine()

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
        return False  # Email already exist

    hashed_pw = hash_password(password)
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO technicians (name, email, password, is_teamlead, activ, admin)
                VALUES (:name, :email, :password, false, true, false)
            """),
            {"name": name, "email": email.lower(), "password": hashed_pw}
        )
    return True

def is_team_lead(user: dict) -> bool:
    return user.get("is_teamlead", False)

def is_admin(user: dict) -> bool:
    return user.get("admin", False)

def decode_email(encoded: str) -> str:
    return base64.urlsafe_b64decode(encoded.encode()).decode()

def encode_email(email: str) -> str:
    return base64.urlsafe_b64encode(email.encode()).decode()

def generate_token(email: str) -> str:
    return secrets.token_urlsafe(32)

def save_token(token: str, user_id: int, expires_at: datetime) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO auth_tokens (token, user_id, expires_at)
                VALUES (:token, :user_id, :expires_at)
                ON CONFLICT (token) DO UPDATE
                SET user_id = EXCLUDED.user_id,
                    expires_at = EXCLUDED.expires_at
            """),
            {"token": token, "user_id": user_id, "expires_at": expires_at}
        )

def get_user_by_token(token: str) -> Optional[dict]:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT t.*
                FROM auth_tokens at
                JOIN technicians t ON at.user_id = t.id
                WHERE at.token = :token AND at.expires_at > NOW()
            """),
            {"token": token}
        ).first()

        if row:
            return dict(row._mapping)
        return None

def delete_user_tokens(user_id: int):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM tokens WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
