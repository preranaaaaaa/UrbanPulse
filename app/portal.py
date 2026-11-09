"""UrbanPulse portal. Run from the project root:  streamlit run app/portal.py"""
import os
import sys
import html
from datetime import datetime

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, os.getcwd())
from nlp.predict import analyze_text

st.set_page_config(page_title="UrbanPulse", layout="wide")

COMPLAINTS, YT, LOG = "data/raw/complaints.csv", "data/raw/youtube_comments.csv", "data/action_log.csv"
COORDS = {"Hampankatta": (12.8696, 74.8433), "Kankanady": (12.8791, 74.8500),
          "Surathkal": (13.0108, 74.7942), "Lalbagh": (12.8860, 74.8420),
          "Bejai": (12.8950, 74.8420), "Kadri": (12.8870, 74.8530),
          "Pumpwell": (12.8630, 74.8630), "Jyothi": (12.8730, 74.8400)}
# category: (department, head, phone, email). DEMO DATA ONLY.
DEPTS = {"Road": ("Roads and Public Works", "A. Rao", "0000-000001", "roads@demo.example"),
         "Drainage": ("Drainage and Sewerage", "S. Shetty", "0000-000002", "drainage@demo.example"),
         "Water": ("Water Supply Board", "M. D'Souza", "0000-000003", "water@demo.example"),
         "Garbage": ("Solid Waste Management", "K. Naik", "0000-000004", "waste@demo.example"),
         "Transport": ("Transport Department", "R. Bhat", "0000-000005", "transport@demo.example"),
         "Other": ("General Grievance Cell", "P. Kamath", "0000-000006", "general@demo.example")}
STATUSES = ["New", "In progress", "Resolved", "Rejected"]
SCORE = {"Angry": -2, "Frustrated": -1, "Neutral": 0, "Satisfied": 1, "Happy": 2}
# DEMO LOGINS: username -> category (None = admin). Password from env, default below.
USERS = {"admin": None, "roads_dept": "Road", "drainage_dept": "Drainage", "water_dept": "Water",
         "waste_dept": "Garbage", "transport_dept": "Transport", "general_dept": "Other"}
PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")


def read(path):
    return pd.read_csv(path, dtype={"id": str, "complaint_id": str}) if os.path.exists(path) else pd.DataFrame()


def append(path, row):
    pd.DataFrame([row]).to_csv(path, mode="a", header=not os.path.exists(path), index=False)


def add_log(cid, status, note, by):
    append(LOG, {"complaint_id": cid, "timestamp": datetime.now().isoformat(timespec="seconds"),
                 "status": status, "note": note, "handled_by": by})


def load():
    df = pd.concat([read(COMPLAINTS), read(YT)], ignore_index=True)
    if df.empty:
        return df
    df["intensity"] = pd.to_numeric(df.get("intensity", 1), errors="coerce").fillna(1)
    df["department"] = df["category"].map(lambda c: DEPTS.get(c, DEPTS["Other"])[0])
    df["score"] = df["emotion"].map(SCORE)
    log = read(LOG)
    df["status"], df["last_updated"] = "New", None
    if not log.empty:
        last = log.sort_values("timestamp").groupby("complaint_id").tail(1).set_index("complaint_id")
        df["status"] = df["id"].map(last["status"]).fillna("New")
        df["last_updated"] = df["id"].map(last["timestamp"])
    return df


# ---------------- public pages ----------------
def page_report():
    st.header("Report a civic issue")
    area = st.selectbox("Area", list(COORDS))
    category = st.selectbox("Category", list(DEPTS))
    text = st.text_area("Describe the problem")
    if st.button("Submit complaint"):
        if not text.strip():
            st.warning("Please describe the problem first.")
            return
        emotion, intensity = analyze_text(text.strip())
        cid = datetime.now().strftime("%m%d-%H%M%S")
        append(COMPLAINTS, {"id": cid, "text": text.strip(), "area": area, "category": category,
                            "source": "form", "timestamp": datetime.now().isoformat(),
                            "intensity": intensity, "emotion": emotion})
        add_log(cid, "New", "Complaint received", "system")
        st.success(f"Thank you. Your complaint ID is {cid}. Keep it to track progress.")


def page_track():
    st.header("Track your complaint")
    cid = st.text_input("Complaint ID").strip()
    if cid:
        log = read(LOG)
        hist = log[log["complaint_id"] == cid] if not log.empty else log
        if hist.empty:
            st.error("No complaint found with that ID.")
        else:
            st.metric("Current status", hist.iloc[-1]["status"])
            st.table(hist[["timestamp", "status", "note"]])


def page_recent():
    st.header("Recent actions taken")
    log, df = read(LOG), load()
    if log.empty or df.empty:
        st.info("No actions yet.")
        return
    done = log[log["status"] == "Resolved"].merge(df[["id", "area", "category"]],
                                                  left_on="complaint_id", right_on="id")
    st.table(done.sort_values("timestamp", ascending=False)
             .head(10)[["timestamp", "area", "category", "note"]])


def page_departments():
    st.header("Departments and contacts")
    st.caption("Demo data. Names and numbers are not real.")
    st.table(pd.DataFrame(DEPTS, index=["Department", "Head", "Phone", "Email"]).T.set_index("Department"))


# ---------------- authority pages ----------------
def color_for(s):
    return "red" if s <= -1 else "orange" if s < -0.3 else "gold" if s <= 0.3 else "green"


def page_overview(df):
    st.header("City overview")
    if st.button("Refresh data"):
        try:
            from collectors.youtube_collector import collect
            with st.spinner("Fetching YouTube comments..."):
                st.success(f"Fetched {collect()} YouTube comments.")
            df = load()
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
    left, right = st.columns([2, 1])
    with left:
        m = folium.Map(location=[12.89, 74.85], zoom_start=12)
        for _, r in g.iterrows():
            if r["area"] in COORDS:
                folium.Circle(COORDS[r["area"]], radius=500 + 120 * r["count"], color=color_for(r["score"]),
                              fill=True, fill_opacity=0.5,
                              popup=f"{r['area']}: score {r['score']:.2f}, {r['count']} complaints").add_to(m)
        st_folium(m, height=420, use_container_width=True)
    with right:
        st.subheader("Priority areas")
        st.dataframe(g.sort_values("priority", ascending=False)[["area", "priority", "score"]],
                     hide_index=True)
    st.subheader("All complaints")
    st.dataframe(df[["id", "text", "area", "department", "source", "emotion", "intensity", "status"]],
                 hide_index=True)


def page_queue(df, user):
    st.header("Department queue")
    cat = USERS[user] or st.selectbox("Department", list(DEPTS))
    st.caption(DEPTS[cat][0])
    if df.empty:
        st.info("No complaints yet.")
        return
    shown = st.multiselect("Status", STATUSES, default=["New", "In progress"])
    q = df[(df["category"] == cat) & (df["status"].isin(shown))].sort_values("intensity", ascending=False)
    st.dataframe(q[["id", "area", "intensity", "emotion", "status", "last_updated"]], hide_index=True)
    if q.empty:
        return
    cid = st.selectbox("Open a complaint", q["id"])
    row = q[q["id"] == cid].iloc[0]
    st.write(f"**{row['area']}** | {row['emotion']} | intensity {int(row['intensity'])}")
    st.info(row["text"])
    status = st.selectbox("Status", STATUSES, index=STATUSES.index(row["status"]))
    note = st.text_input("Note on action taken")
    if st.button("Save update"):
        add_log(cid, status, note, user)
        st.rerun()
    log = read(LOG)
    if not log.empty:
        st.subheader("History")
        st.table(log[log["complaint_id"] == cid][["timestamp", "status", "note", "handled_by"]])
def page_home():
    df, log = load(), read(LOG)
    st.markdown("""<div style="background:linear-gradient(135deg,#0F766E,#134E4A);padding:40px;
        border-radius:16px;margin-bottom:24px">
        <h1 style="margin:0;color:#fff;font-size:36px">Your city. Your voice.</h1>
        <p style="font-size:18px;margin:8px 0 0;color:#D5F0EC">Report potholes, drainage, water and
        garbage problems. Track what is done about them.</p></div>""", unsafe_allow_html=True)

    total = len(df)
    resolved = int((df["status"] == "Resolved").sum()) if total else 0
    areas = df["area"].nunique() if total else 0
    c = st.columns(3)
    c[0].metric("Complaints received", total)
    c[1].metric("Resolved", resolved)
    c[2].metric("Areas covered", areas)

    st.subheader("Recent actions taken")
    done = pd.DataFrame()
    if total and not log.empty:
        done = (log[log["status"] == "Resolved"]
                .merge(df[["id", "area", "category"]], left_on="complaint_id", right_on="id")
                .sort_values("timestamp", ascending=False).head(4))
    if done.empty:
        st.info("No actions recorded yet.")
    else:
        for col, (_, r) in zip(st.columns(len(done)), done.iterrows()):
            note = r["note"] if isinstance(r["note"], str) and r["note"] else "Resolved"
            col.markdown(f"""<div style="background:#fff;border:1px solid #DDE3E9;border-left:5px solid #2E8B57;
                border-radius:12px;padding:16px;min-height:130px"><b>{html.escape(str(r['area']))}</b><br>
                <span style="color:#4A5A68">{html.escape(str(r['category']))}</span>
                <p style="margin:8px 0">{html.escape(note)}</p>
                <small style="color:#4A5A68">{str(r['timestamp'])[:10]}</small></div>""",
                         unsafe_allow_html=True)

    st.subheader("Who to contact")
    st.caption("Demo data. Names and numbers are not real.")
    cols = st.columns(3)
    for i, (cat, (dept, head, phone, email)) in enumerate(DEPTS.items()):
        cols[i % 3].markdown(f"""<div style="background:#fff;border:1px solid #DDE3E9;border-radius:12px;
            padding:16px;margin-bottom:16px"><b style="color:#0F766E">{dept}</b><br>
            <span style="color:#4A5A68">Head: {head}</span><br>{phone}<br>{email}</div>""",
                                unsafe_allow_html=True)

# ---------------- main ----------------
mode = st.sidebar.radio("Portal", ["Public", "Authority"])
if mode == "Public":
    page = st.sidebar.radio("Go to", ["Home", "Report an issue", "Track complaint",
                                      "Recent actions", "Departments"])
    {"Home": page_home, "Report an issue": page_report, "Track complaint": page_track,
     "Recent actions": page_recent, "Departments": page_departments}[page]()
else:
    user = st.session_state.get("user")
    if not user:
        st.sidebar.caption("Demo logins: admin, roads_dept, drainage_dept, water_dept, waste_dept, transport_dept, general_dept")
        u = st.sidebar.text_input("Username")
        p = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Log in"):
            if u in USERS and p == PASSWORD:
                st.session_state["user"] = u
                st.rerun()
            else:
                st.sidebar.error("Wrong username or password.")
        st.header("Authority login")
        st.info("Log in from the sidebar. This is a demo login, not real security.")
    else:
        st.sidebar.write(f"Logged in as **{user}**")
        if st.sidebar.button("Log out"):
            st.session_state.pop("user")
            st.rerun()
        data = load()
        if USERS[user] is None:
            {"Overview": lambda: page_overview(data),
             "Department queue": lambda: page_queue(data, user)}[
                st.sidebar.radio("Go to", ["Overview", "Department queue"])]()
        else:
            page_queue(data, user)
