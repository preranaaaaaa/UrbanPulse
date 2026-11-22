"""UrbanPulse Portal
Run from project root:  streamlit run app/portal.py
"""

import os
import sys
import html
from datetime import datetime

import pandas as pd
import streamlit as st

sys.path.insert(0, os.getcwd())
from nlp.predict import analyze_text
from app import db

# ---------------------------------------------------------------------------
# Page config & global styles
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="UrbanPulse",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()

# Consistent design system
PRIMARY = "#0F766E"       # Deep teal
PRIMARY_DARK = "#134E4A"
ACCENT = "#14B8A6"        # Bright teal
BG_LIGHT = "#F0FDFA"
TEXT_DARK = "#1E293B"
TEXT_MUTED = "#64748B"
CARD_BG = "#FFFFFF"
BORDER = "#E2E8F0"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    .main .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }}

    /* Hide default Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Hero */
    .hero {{
        background: linear-gradient(135deg, {PRIMARY} 0%, {PRIMARY_DARK} 100%);
        border-radius: 20px;
        padding: 48px 40px;
        color: white;
        margin-bottom: 32px;
        box-shadow: 0 10px 40px rgba(15, 118, 110, 0.25);
    }}
    .hero h1 {{
        font-size: 2.6rem;
        font-weight: 700;
        margin: 0 0 12px 0;
        letter-spacing: -0.5px;
    }}
    .hero p {{
        font-size: 1.15rem;
        opacity: 0.92;
        margin: 0;
        max-width: 560px;
        line-height: 1.5;
    }}

    /* Cards */
    .card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 28px 24px;
        height: 100%;
        transition: box-shadow 0.2s, transform 0.2s;
    }}
    .card:hover {{
        box-shadow: 0 8px 30px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }}
    .card h3 {{
        margin: 0 0 8px 0;
        font-size: 1.25rem;
        color: {TEXT_DARK};
    }}
    .card p {{
        color: {TEXT_MUTED};
        font-size: 0.95rem;
        margin: 0 0 20px 0;
        line-height: 1.5;
    }}

    /* Section headers */
    .section-title {{
        font-size: 1.4rem;
        font-weight: 600;
        color: {TEXT_DARK};
        margin: 32px 0 16px 0;
    }}

    /* Info boxes */
    .info-box {{
        background: {BG_LIGHT};
        border-left: 4px solid {ACCENT};
        border-radius: 0 12px 12px 0;
        padding: 16px 20px;
        margin-bottom: 12px;
    }}
    .info-box strong {{
        color: {PRIMARY_DARK};
    }}

    /* Department contact cards */
    .dept-card {{
        background: white;
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }}
    .dept-card h4 {{
        margin: 0 0 6px 0;
        color: {PRIMARY};
        font-size: 1rem;
    }}
    .dept-card p {{
        margin: 2px 0;
        font-size: 0.9rem;
        color: {TEXT_MUTED};
    }}

    /* Status badges */
    .badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }}
    .badge-new {{ background: #DBEAFE; color: #1E40AF; }}
    .badge-progress {{ background: #FEF3C7; color: #92400E; }}
    .badge-resolved {{ background: #D1FAE5; color: #065F46; }}
    .badge-rejected {{ background: #FEE2E2; color: #991B1B; }}

    /* Metric cards */
    .metric-card {{
        background: white;
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 20px;
        text-align: center;
    }}
    .metric-card .value {{
        font-size: 1.8rem;
        font-weight: 700;
        color: {PRIMARY};
    }}
    .metric-card .label {{
        font-size: 0.85rem;
        color: {TEXT_MUTED};
        margin-top: 4px;
    }}

    /* Buttons override */
    .stButton > button {{
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1.4rem;
        border: none;
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {PRIMARY}, {ACCENT});
    }}

    /* Form styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {{
        border-radius: 10px;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {BG_LIGHT};
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        font-weight: 500;
    }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AREAS = ["Hampankatta", "Kankanady", "Surathkal", "Lalbagh",
         "Bejai", "Kadri", "Pumpwell", "Jyothi"]

DEPTS = {
    "Road": ("Roads and Public Works", "A. Rao", "0824-000001", "roads@mangalore.gov.in"),
    "Drainage": ("Drainage and Sewerage", "S. Shetty", "0824-000002", "drainage@mangalore.gov.in"),
    "Water": ("Water Supply Board", "M. D'Souza", "0824-000003", "water@mangalore.gov.in"),
    "Garbage": ("Solid Waste Management", "K. Naik", "0824-000004", "waste@mangalore.gov.in"),
    "Transport": ("Transport Department", "R. Bhat", "0824-000005", "transport@mangalore.gov.in"),
    "Other": ("General Grievance Cell", "P. Kamath", "0824-000006", "general@mangalore.gov.in"),
}

STATUSES = ["New", "In progress", "Resolved", "Rejected"]
SCORE = {"Angry": -2, "Frustrated": -1, "Neutral": 0, "Satisfied": 1, "Happy": 2}

COORDS = {
    "Hampankatta": (12.8696, 74.8433), "Kankanady": (12.8791, 74.8500),
    "Surathkal": (13.0108, 74.7942), "Lalbagh": (12.8860, 74.8420),
    "Bejai": (12.8950, 74.8420), "Kadri": (12.8870, 74.8530),
    "Pumpwell": (12.8630, 74.8630), "Jyothi": (12.8730, 74.8400),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def status_badge(status):
    cls = {
        "New": "badge-new",
        "In progress": "badge-progress",
        "Resolved": "badge-resolved",
        "Rejected": "badge-rejected",
    }.get(status, "badge-new")
    return f'<span class="badge {cls}">{html.escape(status)}</span>'


def load_all():
    df = db.get_complaints()
    if df.empty:
        return df
    df["intensity"] = pd.to_numeric(df.get("intensity", 1), errors="coerce").fillna(1)
    df["department"] = df["category"].map(lambda c: DEPTS.get(c, DEPTS["Other"])[0])
    df["score"] = df["emotion"].map(SCORE)
    log = db.get_log()
    df["status"] = "New"
    df["last_updated"] = None
    if not log.empty:
        last = log.sort_values("timestamp").groupby("complaint_id").tail(1).set_index("complaint_id")
        df["status"] = df["id"].map(last["status"]).fillna("New")
        df["last_updated"] = df["id"].map(last["timestamp"])
    return df


# ---------------------------------------------------------------------------
# HOME PAGE
# ---------------------------------------------------------------------------
def page_home():
    st.markdown("""
    <div class="hero">
        <h1>UrbanPulse</h1>
        <p>Your city. Your voice. Report civic issues, track progress, and help make Mangalore better — one complaint at a time.</p>
    </div>
    """, unsafe_allow_html=True)

    # Entry cards
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
        <div class="card">
            <h3>👤 Public Access</h3>
            <p>Report potholes, drainage problems, garbage issues and more. Track the status of your complaints in real time.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter as Citizen →", key="btn_public", use_container_width=True, type="primary"):
            st.session_state["mode"] = "public"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="card">
            <h3>🏛️ Authority Login</h3>
            <p>Department officers and administrators can manage complaints, update statuses and view city-wide insights.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Authority Login →", key="btn_authority", use_container_width=True):
            st.session_state["mode"] = "authority"
            st.rerun()

    # Awareness section
    st.markdown('<div class="section-title">Public Awareness Guidelines</div>', unsafe_allow_html=True)

    guidelines = [
        ("Report accurately", "Provide clear details and the exact location so authorities can act faster."),
        ("One issue per complaint", "Separate different problems into individual reports for better tracking."),
        ("Follow up politely", "Use the Track section with your Complaint ID. Avoid duplicate submissions."),
        ("Stay safe", "Do not confront contractors or enter restricted areas while reporting."),
        ("Your data is private", "Only you can see the complaints you submit after logging in."),
    ]
    for title, text in guidelines:
        st.markdown(f"""
        <div class="info-box">
            <strong>{title}</strong><br>{text}
        </div>
        """, unsafe_allow_html=True)

    # Department contacts
    st.markdown('<div class="section-title">Department Contacts</div>', unsafe_allow_html=True)
    st.caption("Demo contact details for reference.")

    cols = st.columns(3)
    for i, (cat, (dept, head, phone, email)) in enumerate(DEPTS.items()):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="dept-card">
                <h4>{dept}</h4>
                <p>Head: {head}</p>
                <p>{phone}</p>
                <p>{email}</p>
            </div>
            """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# PUBLIC: Auth
# ---------------------------------------------------------------------------
def public_auth():
    """Show login / signup for public users."""
    st.markdown("""
    <div class="hero" style="padding: 32px 36px;">
        <h1 style="font-size: 1.9rem;">Citizen Portal</h1>
        <p>Sign in to report issues and track only your own complaints.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        with st.form("public_login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
            if submitted:
                user = db.authenticate(username, password, allowed_roles=["public"])
                if user:
                    st.session_state["public_user"] = user
                    st.success(f"Welcome back, {user['username']}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tab_signup:
        with st.form("public_signup"):
            new_user = st.text_input("Choose a username", help="3-30 characters, letters, numbers, underscore")
            new_pass = st.text_input("Choose a password", type="password", help="Minimum 6 characters")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
            if submitted:
                if new_pass != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = db.create_public_user(new_user, new_pass)
                    if ok:
                        st.success(msg)
                        st.info("Now switch to the Log In tab.")
                    else:
                        st.error(msg)

    if st.button("← Back to Home"):
        st.session_state.pop("mode", None)
        st.rerun()


# ---------------------------------------------------------------------------
# PUBLIC: Logged-in pages
# ---------------------------------------------------------------------------
def public_sidebar():
    user = st.session_state["public_user"]
    st.sidebar.markdown(f"**Logged in as**  \n`{user['username']}`")
    page = st.sidebar.radio(
        "Navigate",
        ["Home", "Report a Complaint", "Track Your Complaints"],
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    if st.sidebar.button("Log Out", use_container_width=True):
        st.session_state.pop("public_user", None)
        st.session_state.pop("mode", None)
        st.rerun()
    return page


def public_home(user):
    st.markdown(f"""
    <div class="hero" style="padding: 32px 36px;">
        <h1 style="font-size: 1.9rem;">Welcome, {html.escape(user['username'])}</h1>
        <p>Report civic issues in your area and track the progress of your complaints.</p>
    </div>
    """, unsafe_allow_html=True)

    df = db.get_complaints(user_id=user["id"])
    total = len(df)
    open_count = 0
    resolved = 0
    if not df.empty:
        log = db.get_log()
        if not log.empty:
            last = log.sort_values("timestamp").groupby("complaint_id").tail(1).set_index("complaint_id")
            statuses = df["id"].map(last["status"]).fillna("New")
            open_count = int((~statuses.isin(["Resolved", "Rejected"])).sum())
            resolved = int((statuses == "Resolved").sum())
        else:
            open_count = total

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><div class="value">{total}</div><div class="label">Total Submitted</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><div class="value">{open_count}</div><div class="label">Open</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><div class="value">{resolved}</div><div class="label">Resolved</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Quick Tips</div>', unsafe_allow_html=True)
    tips = [
        "Use the <b>Report a Complaint</b> section to submit a new issue. You will receive a unique Complaint ID.",
        "Go to <b>Track Your Complaints</b> to see status updates on everything you have submitted.",
        "Only you can see your complaints. They are private to your account.",
    ]
    for t in tips:
        st.markdown(f'<div class="info-box">{t}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Department Contacts</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, (cat, (dept, head, phone, email)) in enumerate(DEPTS.items()):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="dept-card">
                <h4>{dept}</h4>
                <p>Head: {head}</p>
                <p>{phone}</p>
                <p>{email}</p>
            </div>
            """, unsafe_allow_html=True)


def public_report(user):
    st.markdown("""
    <div class="hero" style="padding: 28px 36px;">
        <h1 style="font-size: 1.7rem;">Report a Civic Issue</h1>
        <p>Describe the problem clearly. You will receive a Complaint ID after submission.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("report_form"):
        area = st.selectbox("Area", AREAS)
        category = st.selectbox("Category", list(DEPTS.keys()))
        text = st.text_area("Describe the problem", height=140,
                            placeholder="Example: Large pothole near the bus stand on the main road has been there for 2 weeks...")
        submitted = st.form_submit_button("Submit Complaint", type="primary", use_container_width=True)

        if submitted:
            if not text.strip():
                st.warning("Please describe the problem before submitting.")
            else:
                emotion, intensity = analyze_text(text.strip())
                cid = db.new_complaint_id()
                db.add_complaint(
                    cid, text.strip(), area, category, "form",
                    emotion, intensity, user_id=user["id"]
                )
                db.add_log(cid, "New", "Complaint received", "system")
                st.success("Complaint submitted successfully!")
                st.markdown(f"""
                <div class="info-box" style="border-left-color: #059669;">
                    <strong>Your Complaint ID:</strong> <code style="font-size:1.2rem;">{cid}</code><br>
                    Please save this ID. You can track progress in the <b>Track Your Complaints</b> section.
                </div>
                """, unsafe_allow_html=True)


def public_track(user):
    st.markdown("""
    <div class="hero" style="padding: 28px 36px;">
        <h1 style="font-size: 1.7rem;">Track Your Complaints</h1>
        <p>View all complaints you have submitted and their current status.</p>
    </div>
    """, unsafe_allow_html=True)

    df = db.get_complaints(user_id=user["id"])

    if df.empty:
        st.info("You have not submitted any complaints yet. Go to **Report a Complaint** to create one.")
        return

    # Attach latest status
    log = db.get_log()
    if not log.empty:
        last = log.sort_values("timestamp").groupby("complaint_id").tail(1).set_index("complaint_id")
        df["status"] = df["id"].map(last["status"]).fillna("New")
        df["last_updated"] = df["id"].map(last["timestamp"])
    else:
        df["status"] = "New"
        df["last_updated"] = None

    # Summary table
    st.markdown("### Your Complaints")
    display = df[["id", "area", "category", "emotion", "intensity", "status", "timestamp"]].copy()
    display.columns = ["Complaint ID", "Area", "Category", "Emotion", "Intensity", "Status", "Submitted"]
    st.dataframe(display, use_container_width=True, hide_index=True)

    # Detailed view
    st.markdown("### Complaint Details")
    selected = st.selectbox("Select a Complaint ID", df["id"].tolist())
    row = df[df["id"] == selected].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Area:** {row['area']}")
    c2.markdown(f"**Category:** {row['category']}")
    c3.markdown(f"**Status:** {status_badge(row['status'])}", unsafe_allow_html=True)

    st.markdown(f"**Your description:**")
    st.info(row["text"])

    st.markdown(f"**Detected emotion:** {row['emotion']} &nbsp;&nbsp;|&nbsp;&nbsp; **Intensity:** {int(row['intensity'])}/5")

    # History
    hist = db.get_log(complaint_id=selected)
    if not hist.empty:
        st.markdown("#### Status History")
        st.table(hist[["timestamp", "status", "note", "handled_by"]])
    else:
        st.caption("No status updates yet.")


# ---------------------------------------------------------------------------
# AUTHORITY side (kept functional, lightly styled)
# ---------------------------------------------------------------------------
def authority_login():
    st.markdown("""
    <div class="hero" style="padding: 32px 36px;">
        <h1 style="font-size: 1.9rem;">Authority Login</h1>
        <p>Department officers and administrators only.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("auth_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
        if submitted:
            user = db.authenticate(username, password, allowed_roles=["admin", "department"])
            if user:
                st.session_state["authority_user"] = user
                st.rerun()
            else:
                st.error("Invalid credentials or insufficient permissions.")

    st.caption("Demo accounts: admin / roads_dept / drainage_dept / …  (password: demo123)")

    if st.button("← Back to Home"):
        st.session_state.pop("mode", None)
        st.rerun()


def authority_overview(df):
    st.header("City Overview")
    if st.button("Refresh data (YouTube)"):
        try:
            from collectors.youtube_collector import collect
            with st.spinner("Fetching YouTube comments..."):
                fetched = collect()
                db.import_legacy_csvs()
                st.success(f"Fetched {fetched} YouTube comments.")
                st.rerun()
        except Exception as e:
            st.error(f"YouTube fetch failed: {e}")

    if df.empty:
        st.info("No complaints yet.")
        return

    open_df = df[~df["status"].isin(["Resolved", "Rejected"])]
    g = df.groupby("area").agg(score=("score", "mean"), count=("score", "size")).reset_index()
    g["priority"] = g["area"].map(open_df.groupby("area")["intensity"].sum()).fillna(0)
    alerts = g[(g["score"] <= -1) & (g["count"] >= 2)]

    c = st.columns(4)
    c[0].metric("Open complaints", len(open_df))
    c[1].metric("From form", int((df["source"] == "form").sum()))
    c[2].metric("From YouTube", int((df["source"] == "youtube").sum()))
    c[3].metric("Active alerts", len(alerts))

    for _, a in alerts.iterrows():
        st.error(f"ALERT: {a['area']} has high frustration (score {a['score']:.2f}, {a['count']} complaints).")

    try:
        import folium
        from streamlit_folium import st_folium
        left, right = st.columns([2, 1])
        with left:
            m = folium.Map(location=[12.89, 74.85], zoom_start=12)
            for _, r in g.iterrows():
                if r["area"] in COORDS:
                    color = "red" if r["score"] <= -1 else "orange" if r["score"] < -0.3 else "gold" if r["score"] <= 0.3 else "green"
                    folium.Circle(
                        COORDS[r["area"]], radius=500 + 120 * r["count"],
                        color=color, fill=True, fill_opacity=0.5,
                        popup=f"{r['area']}: score {r['score']:.2f}, {r['count']} complaints"
                    ).add_to(m)
            st_folium(m, height=420, use_container_width=True)
        with right:
            st.subheader("Priority areas")
            st.dataframe(g.sort_values("priority", ascending=False)[["area", "priority", "score"]], hide_index=True)
    except ImportError:
        st.warning("Install folium and streamlit-folium for the map view.")

    st.subheader("All complaints")
    st.dataframe(
        df[["id", "text", "area", "department", "source", "emotion", "intensity", "status"]],
        hide_index=True, use_container_width=True
    )


def authority_queue(df, user):
    st.header("Department Queue")
    cat = user.get("category") or st.selectbox("Department", list(DEPTS))
    st.caption(DEPTS[cat][0])

    if df.empty:
        st.info("No complaints yet.")
        return

    shown = st.multiselect("Status filter", STATUSES, default=["New", "In progress"])
    q = df[(df["category"] == cat) & (df["status"].isin(shown))].sort_values("intensity", ascending=False)
    st.dataframe(q[["id", "area", "intensity", "emotion", "status", "last_updated"]], hide_index=True)

    if q.empty:
        return

    cid = st.selectbox("Open a complaint", q["id"])
    row = q[q["id"] == cid].iloc[0]
    st.write(f"**{row['area']}** | {row['emotion']} | intensity {int(row['intensity'])}")
    st.info(row["text"])

    status = st.selectbox("Update status", STATUSES, index=STATUSES.index(row["status"]) if row["status"] in STATUSES else 0)
    note = st.text_input("Note on action taken")
    if st.button("Save update", type="primary"):
        db.add_log(cid, status, note, user["username"])
        st.success("Updated.")
        st.rerun()

    hist = db.get_log(complaint_id=cid)
    if not hist.empty:
        st.subheader("History")
        st.table(hist[["timestamp", "status", "note", "handled_by"]])


def authority_users():
    st.header("Manage Users")
    st.dataframe(pd.DataFrame(db.list_users()), hide_index=True)
    st.subheader("Add a user")
    with st.form("new_user", clear_on_submit=True):
        name = st.text_input("Username")
        email = st.text_input("Email (optional)")
        pw = st.text_input("Password (min 8 characters)", type="password")
        role = st.selectbox("Role", ["department", "admin"])
        cat = st.selectbox("Department (for department role)", list(DEPTS))
        if st.form_submit_button("Create user"):
            ok, msg = db.create_user(name, pw, role, cat, email)
            (st.success if ok else st.error)(msg)


# ---------------------------------------------------------------------------
# MAIN ROUTER
# ---------------------------------------------------------------------------
def main():
    mode = st.session_state.get("mode")

    # ----- Landing / Home -----
    if mode is None:
        page_home()
        return

    # ----- Public flow -----
    if mode == "public":
        if "public_user" not in st.session_state:
            public_auth()
            return

        user = st.session_state["public_user"]
        page = public_sidebar()

        if page == "Home":
            public_home(user)
        elif page == "Report a Complaint":
            public_report(user)
        elif page == "Track Your Complaints":
            public_track(user)
        return

    # ----- Authority flow -----
    if mode == "authority":
        if "authority_user" not in st.session_state:
            authority_login()
            return

        user = st.session_state["authority_user"]
        st.sidebar.markdown(f"**Logged in as**  \n`{user['username']}` ({user['role']})")
        if user["role"] == "admin":
            page = st.sidebar.radio("Navigate", ["Overview", "Department Queue", "Manage Users"])
        else:
            page = st.sidebar.radio("Navigate", ["Department Queue"])

        st.sidebar.divider()
        if st.sidebar.button("Log Out", use_container_width=True):
            st.session_state.pop("authority_user", None)
            st.session_state.pop("mode", None)
            st.rerun()

        data = load_all()

        if page == "Overview":
            authority_overview(data)
        elif page == "Department Queue":
            authority_queue(data, user)
        elif page == "Manage Users":
            authority_users()


if __name__ == "__main__":
    main()
else:
    main()
