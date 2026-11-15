"""UrbanPulse database layer (SQLite). No extra installs needed.

Creates data/urbanpulse.db on first use. Stores authority user accounts with
salted, hashed passwords (never plain text).
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.getenv("URBANPULSE_DB", "data/urbanpulse.db")
ITERATIONS = 200_000
CATEGORIES = ["Road", "Drainage", "Water", "Garbage", "Transport", "Other"]

# Demo accounts created on first run if the users table is empty.
# username -> (category, role). category None = admin (sees every department).
SEED_USERS = {
    "admin": (None, "admin"),
    "roads_dept": ("Road", "department"),
    "drainage_dept": ("Drainage", "department"),
    "water_dept": ("Water", "department"),
    "waste_dept": ("Garbage", "department"),
    "transport_dept": ("Transport", "department"),
    "general_dept": ("Other", "department"),
}


@contextmanager
def connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return salt.hex() + "$" + digest.hex()


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return hmac.compare_digest(check.hex(), digest_hex)


def init_db():
    """Create tables and seed demo users. Safe to call on every run."""
    with connect() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                email         TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL CHECK (role IN ('admin', 'department')),
                category      TEXT,
                created_at    TEXT NOT NULL,
                last_login    TEXT
            )""")
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            pw = os.getenv("DEMO_PASSWORD", "demo123")
            for name, (cat, role) in SEED_USERS.items():
                c.execute(
                    "INSERT INTO users (username, password_hash, role, category, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (name, hash_password(pw), role, cat, datetime.now().isoformat(timespec="seconds")))


def authenticate(username, password):
    """Return the user row (as dict) if credentials are right, else None."""
    with connect() as c:
        row = c.execute("SELECT * FROM users WHERE username = ?",
                        (username.strip().lower(),)).fetchone()
        if row and verify_password(password, row["password_hash"]):
            c.execute("UPDATE users SET last_login = ? WHERE id = ?",
                      (datetime.now().isoformat(timespec="seconds"), row["id"]))
            return dict(row)
    return None


def create_user(username, password, role="department", category=None, email=None):
    """Return (ok, message). Used by the admin 'Manage users' page."""
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
        return False, "Username must be 3-30 characters: letters, numbers, underscore."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if role == "department" and category not in CATEGORIES:
        return False, "Pick a department category."
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "That email doesn't look valid."
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO users (username, email, password_hash, role, category, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (username, email or None, hash_password(password), role,
                 category if role == "department" else None,
                 datetime.now().isoformat(timespec="seconds")))
        return True, f"User '{username}' created."
    except sqlite3.IntegrityError:
        return False, "That username or email is already taken."


def list_users():
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT id, username, email, role, category, created_at, last_login"
            " FROM users ORDER BY id")]


def change_password(username, new_password):
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    with connect() as c:
        n = c.execute("UPDATE users SET password_hash = ? WHERE username = ?",
                      (hash_password(new_password), username)).rowcount
    return (True, "Password updated.") if n else (False, "User not found.")


def delete_user(username):
    with connect() as c:
        c.execute("DELETE FROM users WHERE username = ? AND role != 'admin'", (username,))
