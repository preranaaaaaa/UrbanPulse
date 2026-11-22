"""UrbanPulse database layer (SQLite).

Supports:
- Public users (citizens) with username + password
- Authority users (admin / department)
- Complaints linked to the public user who submitted them
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

# Demo authority accounts created on first run
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
    """Create tables and seed demo authority users. Safe to call on every run."""
    with connect() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                email         TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL CHECK (role IN ('admin', 'department', 'public')),
                category      TEXT,
                created_at    TEXT NOT NULL,
                last_login    TEXT
            )""")

        # Add role 'public' support for existing databases
        try:
            c.execute("ALTER TABLE users ADD COLUMN role TEXT")
        except sqlite3.OperationalError:
            pass

        c.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id        TEXT PRIMARY KEY,
                user_id   INTEGER,
                text      TEXT NOT NULL,
                area      TEXT NOT NULL,
                category  TEXT NOT NULL,
                source    TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                intensity REAL,
                emotion   TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")

        # Add user_id column if missing (for existing DBs)
        try:
            c.execute("ALTER TABLE complaints ADD COLUMN user_id INTEGER")
        except sqlite3.OperationalError:
            pass

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
        c.execute("CREATE INDEX IF NOT EXISTS idx_complaints_user ON complaints (user_id)")

        # Seed authority users only if table is empty
        if c.execute("SELECT COUNT(*) FROM users WHERE role != 'public'").fetchone()[0] == 0:
            pw = os.getenv("DEMO_PASSWORD", "demo123")
            for name, (cat, role) in SEED_USERS.items():
                c.execute(
                    "INSERT OR IGNORE INTO users (username, password_hash, role, category, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (name, hash_password(pw), role, cat, datetime.now().isoformat(timespec="seconds")))

    import_legacy_csvs()


def authenticate(username, password, allowed_roles=None):
    """Return the user row (as dict) if credentials are right, else None.
    allowed_roles: list of roles to accept, e.g. ['public'] or ['admin', 'department']
    """
    with connect() as c:
        row = c.execute(
            "SELECT * FROM users WHERE username = ?",
            (username.strip().lower(),)
        ).fetchone()
        if row and verify_password(password, row["password_hash"]):
            if allowed_roles and row["role"] not in allowed_roles:
                return None
            c.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), row["id"])
            )
            return dict(row)
    return None


def create_public_user(username, password):
    """Create a public (citizen) account. Returns (ok, message)."""
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
        return False, "Username must be 3-30 characters (letters, numbers, underscore only)."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO users (username, password_hash, role, category, created_at)"
                " VALUES (?, ?, 'public', NULL, ?)",
                (username, hash_password(password), datetime.now().isoformat(timespec="seconds"))
            )
        return True, f"Account created successfully. You can now log in as '{username}'."
    except sqlite3.IntegrityError:
        return False, "That username is already taken. Please choose another."


def create_user(username, password, role="department", category=None, email=None):
    """Create an authority user. Returns (ok, message)."""
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
            " FROM users WHERE role != 'public' ORDER BY id")]


def change_password(username, new_password):
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    with connect() as c:
        n = c.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hash_password(new_password), username)
        ).rowcount
    return (True, "Password updated.") if n else (False, "User not found.")


def delete_user(username):
    with connect() as c:
        c.execute("DELETE FROM users WHERE username = ? AND role != 'admin'", (username,))


# ---------------------------------------------------------------- complaints & action log

def new_complaint_id():
    """Short readable ID, e.g. 1122-091530-A7"""
    return f"{datetime.now():%m%d-%H%M%S}-{secrets.token_hex(1).upper()}"


def add_complaint(cid, text, area, category, source, emotion, intensity,
                  user_id=None, timestamp=None):
    with connect() as c:
        c.execute(
            "INSERT INTO complaints (id, user_id, text, area, category, source, timestamp, intensity, emotion)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, user_id, text, area, category, source,
             timestamp or datetime.now().isoformat(timespec="seconds"),
             float(intensity), emotion)
        )


def add_log(complaint_id, status, note, by):
    with connect() as c:
        c.execute(
            "INSERT INTO action_log (complaint_id, timestamp, status, note, handled_by)"
            " VALUES (?, ?, ?, ?, ?)",
            (complaint_id, datetime.now().isoformat(timespec="seconds"), status, note, by)
        )


def get_complaints(user_id=None):
    """If user_id is given, return only that user's complaints. Otherwise all."""
    with connect() as c:
        if user_id is not None:
            return pd.read_sql_query(
                "SELECT * FROM complaints WHERE user_id = ? ORDER BY timestamp DESC",
                c, params=(user_id,)
            )
        return pd.read_sql_query(
            "SELECT * FROM complaints ORDER BY timestamp DESC", c
        )


def get_complaint_by_id(cid, user_id=None):
    """Get a single complaint. If user_id given, only return if it belongs to that user."""
    with connect() as c:
        if user_id is not None:
            row = c.execute(
                "SELECT * FROM complaints WHERE id = ? AND user_id = ?",
                (cid, user_id)
            ).fetchone()
        else:
            row = c.execute(
                "SELECT * FROM complaints WHERE id = ?", (cid,)
            ).fetchone()
        return dict(row) if row else None


def get_log(complaint_id=None):
    with connect() as c:
        if complaint_id:
            return pd.read_sql_query(
                "SELECT complaint_id, timestamp, status, note, handled_by "
                "FROM action_log WHERE complaint_id = ? ORDER BY id",
                c, params=(complaint_id,)
            )
        return pd.read_sql_query(
            "SELECT complaint_id, timestamp, status, note, handled_by "
            "FROM action_log ORDER BY id", c
        )


def import_legacy_csvs():
    """Import old CSV data into the database (no user_id). Safe to call repeatedly."""
    added = 0
    with connect() as c:
        for path, forced_source in (
            ("data/raw/complaints.csv", None),
            ("data/raw/youtube_comments.csv", "youtube"),
        ):
            if not os.path.exists(path):
                continue
            df = pd.read_csv(path, dtype={"id": str})
            df = df.astype(object).where(pd.notna(df), None)
            for r in df.to_dict("records"):
                if not (r.get("id") and r.get("text") and r.get("area") and r.get("category")):
                    continue
                cur = c.execute(
                    "INSERT OR IGNORE INTO complaints "
                    "(id, user_id, text, area, category, source, timestamp, intensity, emotion)"
                    " VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?)",
                    (r["id"], r["text"], r["area"], r["category"],
                     forced_source or r.get("source") or "form",
                     r.get("timestamp") or datetime.now().isoformat(timespec="seconds"),
                     r.get("intensity") or 1, r.get("emotion") or "Neutral")
                )
                added += cur.rowcount

        log_path = "data/action_log.csv"
        if os.path.exists(log_path) and c.execute("SELECT COUNT(*) FROM action_log").fetchone()[0] == 0:
            df = pd.read_csv(log_path, dtype={"complaint_id": str})
            df = df.astype(object).where(pd.notna(df), None)
            for r in df.to_dict("records"):
                c.execute(
                    "INSERT INTO action_log (complaint_id, timestamp, status, note, handled_by)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (r["complaint_id"], r["timestamp"], r["status"], r.get("note"), r.get("handled_by"))
                )
    return added
