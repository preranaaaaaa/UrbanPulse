"""Staff side of UrbanPulse.

Two kinds of login share these pages:
  * Main admin: sees every department, every source (public form and YouTube comments), approves
    resolutions and manages accounts.
  * Department: the same pages, but only that department's complaints. A department cannot close a
    complaint: it sends it to the main admin as "Pending approval". Only when the admin approves does
    the citizen see "Resolved". Permission rules are enforced in db.py, not just hidden in the UI.
"""
import folium
import pandas as pd
import streamlit as st

from app import db, ui
from app.constants import COORDS, DEPTS, OPEN_STATUSES, SCORE, STATUSES

ss = st.session_state
esc = ui.esc
MOOD_COLOURS = [("#B42318", "Very frustrated"), ("#E8772E", "Frustrated"), ("#E6A23C", "Mixed"), ("#1F7A4D", "Positive")]


# ------------------------------------------------------------------ small helpers


def dept_name(category):
    return DEPTS.get(category, DEPTS["Other"])[0]


def short_id(cid):
    return cid if len(cid) <= 16 else cid[:14] + "…"


def age_label(days):
    if days < 1:
        return "Today"
    if days < 60:
        n = int(days)
        return f"{n} day{'s' if n != 1 else ''}"
    if days < 730:
        return f"{int(days // 30)} months"
    return f"{int(days // 365)} years"


def mood_colour(score):
    return MOOD_COLOURS[0][0] if score <= -1 else MOOD_COLOURS[1][0] if score < -0.3 \
        else MOOD_COLOURS[2][0] if score <= 0.3 else MOOD_COLOURS[3][0]


def flash(kind, message):
    ss["flash"] = (kind, message)


def show_flash():
    note = ss.pop("flash", None)
    if note:
        (st.success if note[0] == "ok" else st.error)(note[1])


def when(ts):
    return "No update yet" if ts is None or pd.isna(ts) else ui.fmt_ts(ts)


def empty(message):
    ui.html_block(f'<div class="empty">{esc(message)}</div>')


def table(headers, rows):
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    return ui.h(f'<div class="table-wrap"><table class="mine"><thead><tr>{head}</tr></thead>'
                f'<tbody>{"".join(rows)}</tbody></table></div>')


def prio_badge(label):
    cls = {"High": "high", "Medium": "med", "Low": "low"}.get(label, "none")
    return f'<span class="prio {cls}">{esc(label)}</span>'


def issue_cell(r):
    source = "YouTube comment" if r.source == "youtube" else "Public form"
    text = r.text if len(r.text) <= 110 else r.text[:107] + "…"
    return f'<td class="issue"><b>{esc(short_id(r.id))}</b> <small>{source}</small><br>{esc(text)}</td>'


# ------------------------------------------------------------------ data


def load(user):
    """Every complaint this login may see, with status, mood score and a priority."""
    df = db.get_complaints()
    if df.empty:
        return df
    df["intensity"] = pd.to_numeric(df["intensity"], errors="coerce").fillna(1)
    df["department"] = df["category"].map(dept_name)
    df["score"] = df["emotion"].map(SCORE)
    df["status"], df["last_updated"], df["last_note"], df["last_by"] = "New", None, "", ""
    log = db.get_log()
    if not log.empty:
        last = log.groupby("complaint_id").tail(1).set_index("complaint_id")   # log is ordered oldest to newest
        df["status"] = df["id"].map(last["status"]).fillna("New")
        df["last_updated"] = df["id"].map(last["timestamp"])
        df["last_note"] = df["id"].map(last["note"]).fillna("")
        df["last_by"] = df["id"].map(last["handled_by"]).fillna("")
    if user["role"] == "department":
        df = df[df["category"] == user["category"]].copy()
    # Priority = how strongly it is worded (1 to 5), +1 if a resident reported it through the form (they are
    # waiting for a reply), + up to 2 points for how long it has been open.
    stamp = pd.to_datetime(df["timestamp"], errors="coerce", utc=True, format="ISO8601")
    days = ((pd.Timestamp.now(tz="UTC") - stamp).dt.total_seconds() / 86400).clip(lower=0).fillna(0)
    df["days_open"] = days
    direct = (df["source"] == "form").astype(float)
    score = (df["intensity"] + direct + (days / 3).clip(upper=2)).where(df["status"].isin(OPEN_STATUSES), -1.0)
    df["priority_score"] = score
    df["priority"] = score.map(lambda v: "None" if v < 0 else "High" if v >= 5 else "Medium" if v >= 3.5 else "Low")
    return df


def area_summary(df):
    g = df.groupby("area").agg(score=("score", "mean"), n=("score", "size")).reset_index()
    g["score"] = g["score"].fillna(0)
    return g


# ------------------------------------------------------------------ navigation


def go(page):
    ss["apage"] = page


def logout():
    for key in ("apage", "flash"):
        ss.pop(key, None)
    ss["user"] = None
    ss["page"] = "home"


def topbar(user, page):
    admin = user["role"] == "admin"
    items = [("overview", "Overview"), ("queue", "Department queue")] + ([("users", "Manage users")] if admin else [])
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center", key="topbar"):
        ui.html_block(ui.brand())
        with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", key="topnav"):
            for key, label in items:
                st.button(label, key=f"anav_{key}", type="primary" if page == key else "tertiary",
                          on_click=go, args=(key,))
            ui.html_block(f'<span class="who">{"Main admin" if admin else esc(dept_name(user["category"]))}</span>')
            st.button("Log out", key="anav_logout", type="secondary", on_click=logout)


# ------------------------------------------------------------------ overview


def kpis(df, alerts_n, admin):
    total = len(df)
    form, yt = int((df["source"] == "form").sum()), int((df["source"] == "youtube").sum())
    extra = f"<br>{total - form - yt} from other sources" if total - form - yt else ""
    tiles = [
        f'<div class="kpi total"><span>Total complaints</span><b>{total}</b>'
        f'<small>{form} from the public form<br>{yt} from YouTube comments{extra}</small></div>',
        f'<div class="kpi"><span>Open</span><b>{int(df["status"].isin(OPEN_STATUSES).sum())}</b></div>',
        f'<div class="kpi warn"><span>{"Waiting for approval" if admin else "Sent for approval"}</span>'
        f'<b>{int((df["status"] == "Pending approval").sum())}</b></div>',
        f'<div class="kpi"><span>Resolved</span><b>{int((df["status"] == "Resolved").sum())}</b></div>',
        f'<div class="kpi"><span>Active alerts</span><b>{alerts_n}</b></div>',
    ]
    return ui.h(f'<div class="kpis">{"".join(tiles)}</div>')


def alerts_html(alerts, approvals_waiting=0):
    blocks = []
    if approvals_waiting:
        blocks.append(f'<div class="alert gold"><b>{approvals_waiting} complaint{"s" if approvals_waiting != 1 else ""} '
                      'waiting for your approval.</b> A department has marked them as solved.</div>')
    if alerts.empty:
        blocks.append('<div class="alert calm"><b>No active alerts.</b> No area is showing high frustration right now.</div>')
    for a in alerts.itertuples():
        blocks.append(f'<div class="alert"><b>{esc(a.area)}</b>: residents are very frustrated. {a.n} complaints, '
                      f'average mood {a.score:.1f} on a scale from -2 (angry) to +2 (happy).</div>')
    return ui.h(f'<div class="alerts">{"".join(blocks)}</div>')


def map_page(g):
    m = folium.Map(location=[12.89, 74.85], zoom_start=12, tiles="OpenStreetMap", control_scale=True)
    for r in g.itertuples():
        if r.area not in COORDS:
            continue
        colour = mood_colour(r.score)
        folium.CircleMarker(
            COORDS[r.area], radius=min(40, 12 + 3 * r.n), color=colour, weight=2, fill=True, fill_color=colour,
            fill_opacity=0.5, tooltip=f"{r.area}: {r.n} complaints",
            popup=folium.Popup(f"<b>{esc(r.area)}</b><br>{r.n} complaints<br>Mood score {r.score:.1f}", max_width=240),
        ).add_to(m)
    return m.get_root().render()


def priority_rows(df, admin, limit=10):
    top = df[df["priority_score"] >= 0].sort_values("priority_score", ascending=False).head(limit)
    rows = []
    for r in top.itertuples():
        dept = f"<td>{esc(r.department)}</td>" if admin else ""
        rows.append(f"<tr><td>{prio_badge(r.priority)}</td>{issue_cell(r)}<td>{esc(r.area)}</td>{dept}"
                    f"<td>{esc(r.emotion)}</td><td>{age_label(r.days_open)}</td><td>{ui.badge(r.status)}</td></tr>")
    return rows


def refresh_youtube():
    try:
        from collectors.youtube_collector import collect
        with st.spinner("Fetching YouTube comments..."):
            fetched = collect()
            db.import_legacy_csvs()
        flash("ok", f"Fetched {fetched} YouTube comments.")
    except Exception as exc:  # the collector needs an API key and internet
        flash("error", f"YouTube fetch failed: {exc}")


def render_overview(user, df):
    admin = user["role"] == "admin"
    sub = ("All departments, with complaints from the public form and from YouTube comments in one place." if admin
           else f"{dept_name(user['category'])}. Only complaints for your department are shown.")
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        ui.html_block(ui.page_head("Overview", sub))
        if admin and st.button("Refresh YouTube comments", key="refresh_yt", type="secondary"):
            refresh_youtube()
            df = load(user)
    show_flash()
    if df.empty:
        empty("No complaints yet. They will appear here as soon as residents report problems.")
        return

    g = area_summary(df)
    alerts = g[(g["score"] <= -1) & (g["n"] >= 2)]
    pending = int((df["status"] == "Pending approval").sum())
    ui.html_block(kpis(df, len(alerts), admin))
    ui.html_block(alerts_html(alerts, pending if admin else 0))
    if admin and pending:
        st.button("Review approvals", key="ov_review", type="primary", on_click=go, args=("queue",))

    ui.html_block(ui.section("Map of complaints",
                             "Each circle is an area. Bigger means more complaints, colour shows how people feel."))
    with st.container(key="mapcard"):
        legend = "".join(f'<span><i style="background:{c}"></i>{esc(n)}</span>' for c, n in MOOD_COLOURS)
        ui.html_block(f'<div class="legend">{legend}</div>')
        st.iframe(map_page(g), height=560)

    ui.html_block(ui.section("Priority table", "Open complaints that need attention first."))
    rows = priority_rows(df, admin)
    if rows:
        heads = ["Priority", "Complaint", "Area"] + (["Department"] if admin else []) + ["Mood", "Open for", "Status"]
        ui.html_block(table(heads, rows))
        ui.html_block('<p class="how">Priority adds up how strongly the complaint is worded (1 to 5), 1 point if a resident '
                      'reported it through the form and is waiting for a reply, and up to 2 points for how long it has been '
                      'open. 5 or more is High, 3.5 or more is Medium.</p>')
    else:
        empty("No open complaints. Everything has been resolved or is waiting for approval.")

    if admin:
        ui.html_block(ui.section("By department"))
        rows = []
        for cat, (name, *_rest) in DEPTS.items():
            d = df[df["category"] == cat]
            rows.append(f'<tr><td class="id">{esc(name)}</td><td>{len(d)}</td>'
                        f'<td>{int(d["status"].isin(OPEN_STATUSES).sum())}</td>'
                        f'<td>{int((d["status"] == "Pending approval").sum())}</td>'
                        f'<td>{int((d["status"] == "Resolved").sum())}</td></tr>')
        ui.html_block(table(["Department", "Total", "Open", "Waiting for approval", "Resolved"], rows))


# ------------------------------------------------------------------ department queue and approvals


def approvals(user, df):
    pend = df[df["status"] == "Pending approval"].sort_values("last_updated")
    ui.html_block(ui.section("Waiting for your approval",
                             "Departments mark a problem as solved here. Residents see Resolved only after you approve."))
    if pend.empty:
        empty("Nothing is waiting for approval. When a department marks a problem as solved, it will appear here.")
        return
    for n, r in enumerate(pend.head(20).itertuples()):
        with st.container(key=f"apv_{n}"):
            note = (f'<div class="dnote"><b>{esc(r.last_by)}</b> wrote: {ui.esc_multiline(r.last_note)}</div>'
                    if r.last_note else "")
            ui.html_block(f'<div class="approve"><div class="top"><b>{esc(short_id(r.id))}</b>'
                          f'<span>{esc(r.department)}, {esc(r.area)}. Sent {ui.fmt_ts(r.last_updated)}</span></div>'
                          f'<p>{ui.esc_multiline(r.text)}</p>{note}</div>')
            with st.form(f"approve_{r.id}"):
                reply = st.text_input("Note for the resident (optional)", key=f"apn_{r.id}")
                a, b = st.columns(2)
                yes = a.form_submit_button("Approve as resolved", type="primary", width="stretch")
                back = b.form_submit_button("Send back for more work", width="stretch")
            if yes or back:
                ok, msg = db.review_resolution(user, r.id, approve=yes, note=reply)
                flash("ok" if ok else "error", msg)
                st.rerun()

def update_form(user, r):
    admin = user["role"] == "admin"
    preview_key = f"related_preview_{r.id}"
    confirm_key = f"confirm_related_{r.id}"

    # Department users cannot update complaints awaiting approval or already closed.
    if not admin:
        if r.status == "Pending approval":
            ui.html_block(
                '<div class="alerts"><div class="alert gold">'
                '<b>Waiting for the main admin.</b> You sent this as solved. '
                'Residents will see Resolved once it is approved.'
                '</div></div>'
            )
            return

        if r.status in ("Resolved", "Rejected"):
            empty(f"This complaint is {r.status.lower()}. No further updates are needed.")
            return

    # Find related complaints and save the preview in session state.
    if st.button("Preview related complaints", key=f"preview_button_{r.id}"):
        st.session_state[preview_key] = db.get_related_complaints(r.id)
        st.session_state[confirm_key] = False
        st.rerun()

    related_ids = st.session_state.get(preview_key)

    if related_ids is None:
        st.info("Click 'Preview related complaints' before saving an update.")
        return

    if not related_ids:
        st.warning("No open related complaints were found. Please refresh the preview.")
        return

    # Show the exact complaints included in the preview.
    complaints = db.get_complaints()
    matches = complaints[complaints["id"].isin(related_ids)]

    st.write(f"**Preview: {len(matches)} complaint(s) will be updated**")
    st.dataframe(
        matches[["id", "text", "area", "category"]],
        hide_index=True,
        use_container_width=True
    )

    # Keep the checkbox OUTSIDE the form so Streamlit updates it immediately.
    confirmed = st.checkbox(
        "I checked the preview and want to update all listed complaints.",
        key=confirm_key
    )

    with st.form(f"update_{r.id}"):
        if admin:
            status_options = list(STATUSES)
            current_index = (
                status_options.index(r.status)
                if r.status in status_options
                else 0
            )

            status = st.selectbox(
                "Status",
                status_options,
                index=current_index
            )
        else:
            choice = st.radio(
                "What is the update?",
                [
                    "Work has started",
                    "Problem solved, send to the main admin for approval"
                ]
            )

            status = (
                "In progress"
                if choice == "Work has started"
                else "Pending approval"
            )

        note = st.text_area(
            "Note on the action taken",
            height=90,
            help="Residents can read this note when they track their complaint."
        )

        saved = st.form_submit_button(
            "Save update",
            type="primary"
        )

    if saved:
        if not confirmed:
            st.warning("Please check the confirmation box above before saving.")
            return

        ok, msg = db.update_complaint_status(
            user,
            r.id,
            status,
            note,
            related_ids=related_ids
        )

        if ok:
            st.session_state.pop(preview_key, None)
            st.session_state.pop(confirm_key, None)
            flash("ok", msg)
            st.rerun()
        else:
            st.error(msg)
            
def history(cid):
    log = db.get_log()
    log = log[log["complaint_id"] == cid]
    items = "".join(
        f'<li><b>{esc(x.status)}</b><small>{ui.fmt_ts(x.timestamp)} by '
        f'<em>{"Received" if x.handled_by == "system" else esc(x.handled_by)}</em></small>'
        f'{"<span>" + ui.esc_multiline(x.note) + "</span>" if isinstance(x.note, str) and x.note.strip() else ""}</li>'
        for x in log.itertuples())
    return ui.h(f'<div class="detail"><div class="tl-title" style="margin-top:0">History</div><ul class="tl">{items}</ul></div>')


def render_queue(user, df):
    admin = user["role"] == "admin"
    sub = ("Complaints for every department. Review approvals first, then work through the queue." if admin
           else f"{dept_name(user['category'])}. Update the status and send solved problems to the main admin.")
    ui.html_block(ui.page_head("Department queue", sub))
    show_flash()
    if df.empty:
        empty("No complaints yet.")
        return
    if admin:
        approvals(user, df)
        ui.html_block(ui.section("All complaints"))

    c1, c2, c3 = st.columns([1.2, 1.5, 1])
    if admin:
        pick = c1.selectbox("Department", ["All departments"] + [d[0] for d in DEPTS.values()])
    else:
        c1.selectbox("Department", [dept_name(user["category"])], disabled=True)
        pick = None
    statuses = c2.multiselect("Status", STATUSES, default=["New", "In progress", "Pending approval"])
    source = c3.selectbox("Source", ["All sources", "Public form", "YouTube comments"])

    q = df[df["status"].isin(statuses)]
    if pick and pick != "All departments":
        q = q[q["department"] == pick]
    if source != "All sources":
        q = q[q["source"] == ("form" if source == "Public form" else "youtube")]
    q = q.sort_values(["priority_score", "timestamp"], ascending=[False, False])
    if q.empty:
        empty("No complaints match these filters.")
        return

    rows = []
    for r in q.head(50).itertuples():
        dept = f"<td>{esc(r.department)}</td>" if admin else ""
        rows.append(f"<tr><td>{prio_badge(r.priority)}</td>{issue_cell(r)}<td>{esc(r.area)}</td>{dept}"
                    f"<td>{esc(r.emotion)}</td><td>{ui.badge(r.status)}</td><td>{when(r.last_updated)}</td></tr>")
    heads = ["Priority", "Complaint", "Area"] + (["Department"] if admin else []) + ["Mood", "Status", "Last update"]
    ui.html_block(table(heads, rows))
    ui.html_block(f'<p class="how">Showing {min(50, len(q))} of {len(q)}, highest priority first.</p>')

    ids = list(q["id"].head(200))
    labels = {r.id: f"{short_id(r.id)}  |  {r.area}  |  {r.text[:60]}" for r in q.head(200).itertuples()}
    ui.html_block(ui.section("Open a complaint"))
    cid = st.selectbox("Complaint", ids, format_func=lambda i: labels[i], label_visibility="collapsed")
    r = next(x for x in q.itertuples() if x.id == cid)
    source_text = "YouTube comment" if r.source == "youtube" else "Public form"
    ui.html_block(f'<div class="detail"><div class="detail-head"><b>{esc(short_id(r.id))}</b>{ui.badge(r.status)}</div>'
                  f'<p class="result-meta" style="margin:8px 0 0">{esc(r.department)}. {esc(r.area)}. {source_text}. '
                  f'Mood: {esc(r.emotion)}, intensity {int(r.intensity)}. Received {ui.fmt_ts(r.timestamp)}.</p>'
                  f'<div class="result-text">{ui.esc_multiline(r.text)}</div></div>')
    update_form(user, r)
    ui.html_block(history(cid))


# ------------------------------------------------------------------ manage users (main admin only)


def render_users():
    ui.html_block(ui.page_head("Manage users",
                               "Staff accounts. Each department logs in with its department name and password."))
    rows = [f'<tr><td class="id">{esc(u["username"])}</td><td>{"Main admin" if u["role"] == "admin" else "Department"}</td>'
            f'<td>{esc(dept_name(u["category"])) if u["category"] else "All departments"}</td>'
            f'<td>{esc(u["email"] or "")}</td><td>{ui.fmt_ts(u["last_login"]) if u["last_login"] else "Never"}</td></tr>'
            for u in db.list_users()]
    ui.html_block(table(["Username", "Role", "Department", "Email", "Last login"], rows))
    left, right = st.columns(2, gap="large")
    with left, st.container(key="formcard"):
        ui.html_block('<div class="auth-title" style="margin-top:0">Add a user</div>')
        with st.form("new_user", clear_on_submit=True):
            name = st.text_input("Username")
            email = st.text_input("Email (optional)")
            pw = st.text_input("Password (at least 8 characters)", type="password")
            role = st.selectbox("Role", ["department", "admin"])
            cat = st.selectbox("Department (for the department role)", list(DEPTS), format_func=dept_name)
            if st.form_submit_button("Create user", type="primary"):
                ok, msg = db.create_user(name, pw, role, cat, email)
                (st.success if ok else st.error)(msg)
    with right, st.container(key="trackcard"):
        ui.html_block('<div class="auth-title" style="margin-top:0">Reset a password</div>')
        with st.form("reset_pw", clear_on_submit=True):
            who = st.selectbox("User", [u["username"] for u in db.list_users()])
            new_pw = st.text_input("New password (at least 8 characters)", type="password")
            if st.form_submit_button("Reset password", type="primary"):
                ok, msg = db.change_password(who, new_pw)
                (st.success if ok else st.error)(msg)


# ------------------------------------------------------------------ router


def render(user):
    page = ss.get("apage", "overview")
    if page not in ("overview", "queue", "users") or (page == "users" and user["role"] != "admin"):
        page = ss["apage"] = "overview"
    topbar(user, page)
    if page == "users":
        render_users()
        return
    df = load(user)
    (render_overview if page == "overview" else render_queue)(user, df)
