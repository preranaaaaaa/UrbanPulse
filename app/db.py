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

import pandas as pd

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
        c.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id        TEXT PRIMARY KEY,
                text      TEXT NOT NULL,
                area      TEXT NOT NULL,
                category  TEXT NOT NULL,
                source    TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                intensity REAL,
                emotion   TEXT
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS action_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id TEXT NOT NULL,
                timestamp    TEXT NOT NULL,
                status       TEXT NOT NULL,
                note         TEXT,
                handled_by   TEXT
            )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_log_complaint ON action_log (complaint_id)")
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            pw = os.getenv("DEMO_PASSWORD", "demo123")
            for name, (cat, role) in SEED_USERS.items():
                c.execute(
                    "INSERT INTO users (username, password_hash, role, category, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (name, hash_password(pw), role, cat, datetime.now().isoformat(timespec="seconds")))
    import_legacy_csvs()


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


# ---------------------------------------------------------------- complaints & action log
def new_complaint_id():
    """Short readable ID, e.g. 1118-193045-A7 (random suffix avoids clashes in the same second)."""
    return f"{datetime.now():%m%d-%H%M%S}-{secrets.token_hex(1).upper()}"


def add_complaint(cid, text, area, category, source, emotion, intensity, timestamp=None):
    with connect() as c:
        c.execute("INSERT INTO complaints (id, text, area, category, source, timestamp, intensity, emotion)"
                  " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (cid, text, area, category, source,
                   timestamp or datetime.now().isoformat(timespec="seconds"), float(intensity), emotion))


def add_log(complaint_id, status, note, by):
    with connect() as c:
        c.execute("INSERT INTO action_log (complaint_id, timestamp, status, note, handled_by)"
                  " VALUES (?, ?, ?, ?, ?)",
                  (complaint_id, datetime.now().isoformat(timespec="seconds"), status, note, by))


def get_complaints():
    with connect() as c:
        return pd.read_sql_query("SELECT * FROM complaints ORDER BY timestamp", c)


def get_log():
    with connect() as c:
        return pd.read_sql_query(
            "SELECT complaint_id, timestamp, status, note, handled_by FROM action_log ORDER BY id", c)


def import_legacy_csvs():
    """Copy rows from the old CSV files into the database. Safe to call repeatedly.

    complaints.csv and youtube_comments.csv are synced by id (duplicates ignored), so this is
    also how newly collected YouTube comments reach the database. action_log.csv is imported
    once, only while the action_log table is still empty. Returns number of new complaints.
    """
    added = 0
    with connect() as c:
        for path, forced_source in (("data/raw/complaints.csv", None),
                                    ("data/raw/youtube_comments.csv", "youtube")):
            if not os.path.exists(path):
                continue
            df = pd.read_csv(path, dtype={"id": str})
            df = df.astype(object).where(pd.notna(df), None)
            for r in df.to_dict("records"):
                if not (r.get("id") and r.get("text") and r.get("area") and r.get("category")):
                    continue
                cur = c.execute(
                    "INSERT OR IGNORE INTO complaints (id, text, area, category, source, timestamp, intensity, emotion)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (r["id"], r["text"], r["area"], r["category"], forced_source or r.get("source") or "form",
                     r.get("timestamp") or datetime.now().isoformat(timespec="seconds"),
                     r.get("intensity") or 1, r.get("emotion") or "Neutral"))
                added += cur.rowcount
        log_path = "data/action_log.csv"
        if os.path.exists(log_path) and c.execute("SELECT COUNT(*) FROM action_log").fetchone()[0] == 0:
            df = pd.read_csv(log_path, dtype={"complaint_id": str})
            df = df.astype(object).where(pd.notna(df), None)
            for r in df.to_dict("records"):
                c.execute("INSERT INTO action_log (complaint_id, timestamp, status, note, handled_by)"
                          " VALUES (?, ?, ?, ?, ?)",
                          (r["complaint_id"], r["timestamp"], r["status"], r.get("note"), r.get("handled_by")))
    return added
