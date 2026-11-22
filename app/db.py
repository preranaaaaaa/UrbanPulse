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
from difflib import SequenceMatcher
import pandas as pd

from app.constants import STATUSES

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
        c.execute("""
            CREATE TABLE IF NOT EXISTS public_users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name     TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                phone         TEXT,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL,
                last_login    TEXT
            )""")
        # Older databases have no owner column on complaints: add it once.
        cols = {r[1] for r in c.execute("PRAGMA table_info(complaints)")}
        if "user_id" not in cols:
            c.execute("ALTER TABLE complaints ADD COLUMN user_id INTEGER")
        c.execute("CREATE INDEX IF NOT EXISTS idx_complaints_user ON complaints (user_id)")
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


# ---------------------------------------------------------------- staff: department login and approvals
def authenticate_department(category, password):
    """Log in a department by its category (e.g. 'Road') and password. Returns the user dict or None."""
    with connect() as c:
        rows = c.execute("SELECT * FROM users WHERE role = 'department' AND category = ?", (category,)).fetchall()
        match = None
        for row in rows:               # a department may have more than one account
            if verify_password(password or "", row["password_hash"]):
                match = row
        if not rows:
            verify_password(password or "", _DUMMY_HASH)
        if match:
            c.execute("UPDATE users SET last_login = ? WHERE id = ?",
                      (datetime.now().isoformat(timespec="seconds"), match["id"]))
            return dict(match)
    return None


def _current_status(c, complaint_id):
    row = c.execute("SELECT status FROM action_log WHERE complaint_id = ? ORDER BY id DESC LIMIT 1",
                    (complaint_id,)).fetchone()
    return row["status"] if row else "New"

def get_related_complaints(complaint_id, threshold=0.72):
    """Find open complaints likely describing the same issue."""
    with connect() as c:
        selected = c.execute(
            "SELECT id, text, category, area FROM complaints WHERE id = ?",
            (complaint_id,)
        ).fetchone()

        if not selected:
            return []

        def normalize(text):
            return " ".join(re.findall(r"\w+", (text or "").lower()))

        target_text = normalize(selected["text"])
        if not target_text:
            return [complaint_id]

        rows = c.execute("""
            SELECT c.id, c.text, c.category, c.area,
                   COALESCE((
                       SELECT l.status
                       FROM action_log l
                       WHERE l.complaint_id = c.id
                       ORDER BY l.id DESC
                       LIMIT 1
                   ), 'New') AS status
            FROM complaints c
            WHERE c.category = ? AND c.area = ?
        """, (selected["category"], selected["area"])).fetchall()

        related = []
        for row in rows:
            if row["status"] in ("Resolved", "Rejected"):
                continue

            candidate = normalize(row["text"])
            similarity = SequenceMatcher(
                None, target_text, candidate
            ).ratio()

            if row["id"] == complaint_id or similarity >= threshold:
                related.append(row["id"])

        return related

def update_complaint_status(user, complaint_id, status, note="", related_ids=None):
    """Update the selected complaint and the exact related complaints previewed by staff."""
    note = (note or "").strip()

    if related_ids is None:
        return False, "Please preview related complaints before saving."

    # Re-check the related group at save time.
    current_related = get_related_complaints(complaint_id)
    expected_ids = set(current_related or [complaint_id])
    selected_ids = set(related_ids)

    if selected_ids != expected_ids:
        return False, "The related complaints changed. Please preview them again."

    now = datetime.now().isoformat(timespec="seconds")

    with connect() as c:
        if user["role"] == "department":
            if status not in ("In progress", "Pending approval"):
                return False, "A department can set In progress or send a complaint for approval."

            if status == "Pending approval" and not note:
                return False, "Write a short note on the work done before sending it for approval."

        elif user["role"] != "admin" or status not in STATUSES:
            return False, "You do not have permission to do that."

        # Validate every complaint before writing any updates.
        for cid in selected_ids:
            row = c.execute(
                "SELECT category FROM complaints WHERE id = ?",
                (cid,)
            ).fetchone()

            if not row:
                return False, f"Complaint {cid} was not found."

            current_status = _current_status(c, cid)

            if user["role"] == "department":
                if row["category"] != user["category"]:
                    return False, "A related complaint belongs to another department."

                if current_status == "Pending approval":
                    return False, "A related complaint is already waiting for admin approval."

                if current_status in ("Resolved", "Rejected"):
                    return False, "A related complaint is already closed."

        # All checks passed: update the whole group.
        for cid in selected_ids:
            c.execute(
                """
                INSERT INTO action_log
                    (complaint_id, timestamp, status, note, handled_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cid, now, status, note, user["username"])
            )

    return True, f"Update saved for {len(selected_ids)} complaint(s)."

def review_resolution(user, complaint_id, approve, note=""):
    """Main admin approves a department's 'problem solved' claim (-> Resolved, visible to the citizen)
    or sends it back for more work (-> In progress). Returns (ok, message)."""
    if user["role"] != "admin":
        return False, "Only the main admin can approve a resolution."
    note = (note or "").strip()
    with connect() as c:
        if _current_status(c, complaint_id) != "Pending approval":
            return False, "This complaint is not waiting for approval."
        status = "Resolved" if approve else "In progress"
        text = note or ("Resolution checked and approved." if approve else "More work is needed.")
        if not approve:
            text = "Sent back for more work: " + text
        c.execute("INSERT INTO action_log (complaint_id, timestamp, status, note, handled_by) VALUES (?, ?, ?, ?, ?)",
                  (complaint_id, datetime.now().isoformat(timespec="seconds"), status, text, user["username"]))
    return True, "Approved. The citizen will now see it as resolved." if approve else "Sent back to the department."


# ---------------------------------------------------------------- public (citizen) accounts
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_DUMMY_HASH = hash_password("not-a-real-password")


def _public_dict(row):
    d = dict(row)
    d.pop("password_hash", None)
    return d


def create_public_user(full_name, email, password, phone=None):
    """Return (ok, message, user_dict_or_None). Used by the public Sign up form."""
    full_name = " ".join((full_name or "").split())
    email = (email or "").strip().lower()
    phone = re.sub(r"[\s-]", "", phone or "")
    if not 2 <= len(full_name) <= 60:
        return False, "Enter your full name (2 to 60 characters).", None
    if not EMAIL_RE.fullmatch(email) or len(email) > 120:
        return False, "That email address doesn't look valid.", None
    if phone and not re.fullmatch(r"\+?\d{10,13}", phone):
        return False, "Enter a valid phone number, or leave it empty.", None
    if len(password or "") < 8:
        return False, "Password must be at least 8 characters.", None
    try:
        with connect() as c:
            cur = c.execute(
                "INSERT INTO public_users (full_name, email, phone, password_hash, created_at, last_login)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (full_name, email, phone or None, hash_password(password),
                 datetime.now().isoformat(timespec="seconds"),
                 datetime.now().isoformat(timespec="seconds")))
            row = c.execute("SELECT * FROM public_users WHERE id = ?", (cur.lastrowid,)).fetchone()
        return True, "Account created.", _public_dict(row)
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists. Please log in instead.", None


def authenticate_public(email, password):
    """Return the citizen (dict without password hash) if email and password match, else None."""
    email = (email or "").strip().lower()
    with connect() as c:
        row = c.execute("SELECT * FROM public_users WHERE email = ?", (email,)).fetchone()
        # Always run one hash check so a wrong email and a wrong password take the same time.
        ok = verify_password(password or "", row["password_hash"] if row else _DUMMY_HASH)
        if row and ok:
            c.execute("UPDATE public_users SET last_login = ? WHERE id = ?",
                      (datetime.now().isoformat(timespec="seconds"), row["id"]))
            return _public_dict(row)
    return None


# ---------------------------------------------------------------- owner-scoped complaint access
_RAW_STATUS = ("COALESCE((SELECT l.status FROM action_log l WHERE l.complaint_id = c.id"
               " ORDER BY l.id DESC LIMIT 1), 'New')")
# What a citizen sees: work that is waiting for the main admin's approval still counts as In progress.
_STATUS_SQL = f"CASE WHEN {_RAW_STATUS} = 'Pending approval' THEN 'In progress' ELSE {_RAW_STATUS} END"


def create_complaint(text, area, category, emotion, intensity, user_id=None, source="form"):
    """Save a complaint and its first 'New' log entry in one transaction. Returns the complaint ID."""
    with connect() as c:
        for _ in range(8):  # a clashing ID is very unlikely; just try again with a fresh one
            cid = new_complaint_id()
            try:
                c.execute(
                    "INSERT INTO complaints (id, text, area, category, source, timestamp, intensity, emotion, user_id)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (cid, text, area, category, source, datetime.now().isoformat(timespec="seconds"),
                     float(intensity), emotion, user_id))
                break
            except sqlite3.IntegrityError:
                continue
        else:
            raise RuntimeError("Could not generate a unique complaint ID.")
        c.execute("INSERT INTO action_log (complaint_id, timestamp, status, note, handled_by)"
                  " VALUES (?, ?, ?, ?, ?)",
                  (cid, datetime.now().isoformat(timespec="seconds"), "New", "Complaint received", "system"))
    return cid


def get_user_complaints(user_id):
    """All complaints filed by this citizen (newest first), each with its current status."""
    with connect() as c:
        return pd.read_sql_query(
            f"SELECT c.id, c.text, c.area, c.category, c.timestamp, c.emotion, c.intensity,"
            f" {_STATUS_SQL} AS status FROM complaints c WHERE c.user_id = ? ORDER BY c.timestamp DESC, c.id DESC",
            c, params=(user_id,))


def get_user_complaint(user_id, complaint_id):
    """One complaint, but only if it belongs to this citizen. Otherwise None."""
    with connect() as c:
        row = c.execute(
            f"SELECT c.id, c.text, c.area, c.category, c.timestamp, c.emotion, c.intensity,"
            f" {_STATUS_SQL} AS status FROM complaints c WHERE c.id = ? AND c.user_id = ?",
            ((complaint_id or "").strip(), user_id)).fetchone()
    return dict(row) if row else None


def get_complaint_log(complaint_id):
    """Status history of one complaint (call get_user_complaint first to check ownership)."""
    with connect() as c:
        return pd.read_sql_query(
            "SELECT timestamp, status, note FROM action_log WHERE complaint_id = ? AND status != 'Pending approval' ORDER BY id",
            c, params=(complaint_id,))


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
