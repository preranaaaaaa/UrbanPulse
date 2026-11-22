"""Public side of UrbanPulse: home, sign up / log in, report a complaint, track your complaint.

Every complaint is saved with the ID of the citizen who filed it. Citizens can only ever read
complaints that carry their own ID (see db.get_user_complaints / db.get_user_complaint).
"""
import streamlit as st

from app import db, ui
from app.constants import COORDS, DEPTS
from nlp.predict import analyze_text

ss = st.session_state


# ------------------------------------------------------------------ navigation


def go(page, **state):
    """Button callback: switch page (and optionally set session values) before the next run."""
    ss.pop("just_reported", None)
    ss["page"] = page
    for key, value in state.items():
        ss[key] = value


def set_mode(mode):
    ss["auth_mode"] = mode


def logout_public():
    for key in ("pub_user", "tracked_id", "track_id_input", "just_reported", "auth_mode"):
        ss.pop(key, None)
    ss["page"] = "home"


def topbar():
    user, page = ss.get("pub_user"), ss.get("page", "home")
    with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center", key="topbar"):
        ui.html_block(ui.brand())
        with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", key="topnav"):
            if user:
                items = [("home", "Home", {}), ("report", "Report a complaint", {}),
                         ("track", "Track your complaint", {})]
            else:
                items = [("home", "Home", {}), ("auth_public", "Public login", {"auth_mode": "login"}),
                         ("auth_authority", "Admin login", {})]
            for key, label, state in items:
                st.button(label, key=f"nav_{key}", type="primary" if page == key else "tertiary",
                          on_click=go, args=(key,), kwargs=state)
            if user:
                st.button("Log out", key="nav_logout", type="secondary", on_click=logout_public)


# ------------------------------------------------------------------ home


def render_home():
    user = ss.get("pub_user")
    if user:
        counts = db.get_user_complaints(user["id"])["status"].value_counts().to_dict()
        ui.html_block(ui.welcome_banner(user["full_name"].split()[0], counts))
        with st.container(horizontal=True):
            st.button("Report a complaint", key="home_report", type="primary", on_click=go, args=("report",))
            st.button("Track your complaint", key="home_track", type="secondary", on_click=go, args=("track",))
    else:
        ui.html_block(ui.hero_guest())
        with st.container(key="portals"):
            left, right = st.columns(2, gap="medium")
            with left, st.container(key="portal_public"):
                ui.html_block('<div class="portal-title">Public portal</div>'
                              '<p class="portal-text">For residents. Sign up once, then report problems '
                              'and track each one with its complaint ID.</p>')
                with st.container(horizontal=True):
                    st.button("Sign up", key="home_signup", type="primary", on_click=go,
                              args=("auth_public",), kwargs={"auth_mode": "signup"})
                    st.button("Log in", key="home_login", type="secondary", on_click=go,
                              args=("auth_public",), kwargs={"auth_mode": "login"})
            with right, st.container(key="portal_authority"):
                ui.html_block('<div class="portal-title">Admin portal</div>'
                              '<p class="portal-text">For department staff and administrators. Log in to '
                              'review complaints, record the action taken and update their status.</p>')
                with st.container(horizontal=True):
                    st.button("Admin login", key="home_admin", type="primary", on_click=go, args=("auth_authority",))
        ui.html_block(ui.section("How it works"))
        ui.html_block(ui.how_it_works())

    ui.html_block(ui.section("Before you report",
                             "A few habits that get problems fixed faster and keep Mangaluru safe and clean."))
    ui.html_block(ui.guidelines())
    ui.html_block(ui.emergency())
    ui.html_block(ui.section("Who to contact", "Each complaint category is handled by one department."))
    ui.html_block(ui.departments(DEPTS))
    ui.html_block(ui.footer())


# ------------------------------------------------------------------ sign up / log in


def _finish_login(user):
    ss["pub_user"] = user
    ss["user"] = None
    ss["page"] = "home"
    st.rerun()


def render_auth():
    mode = ss.get("auth_mode", "login")
    left, right = st.columns([5, 6], gap="large")
    with left:
        if mode == "signup":
            ui.html_block(ui.auth_side(
                "Your voice, on record",
                "Create a free account to report civic problems in your area.",
                ["Get a complaint ID for every problem you report",
                 "Follow each complaint from received to resolved",
                 "Only you can see the complaints you file"]))
        else:
            ui.html_block(ui.auth_side(
                "Welcome back",
                "Log in to report a problem or check on one you already filed.",
                ["Track any complaint with its ID",
                 "See what action the department has taken",
                 "Your complaints stay private to your account"]))
    with right, st.container(key="authcard"):
        with st.container(key="authtabs"):
            a, b = st.columns(2, gap="small")
            a.button("Sign up", key="tab_signup", type="primary" if mode == "signup" else "tertiary",
                     width="stretch", on_click=set_mode, args=("signup",))
            b.button("Log in", key="tab_login", type="primary" if mode == "login" else "tertiary",
                     width="stretch", on_click=set_mode, args=("login",))

        if mode == "signup":
            ui.html_block('<div class="auth-title">Create your account</div>'
                          '<p class="auth-sub">Already have one? Choose Log in above.</p>')
            with st.form("signup_form"):
                name = st.text_input("Full name", key="su_name", autocomplete="name")
                email = st.text_input("Email", key="su_email", autocomplete="email")
                phone = st.text_input("Phone number (optional)", key="su_phone", autocomplete="tel")
                pw = st.text_input("Password", type="password", key="su_pw", autocomplete="new-password",
                                   help="At least 8 characters.")
                pw2 = st.text_input("Confirm password", type="password", key="su_pw2", autocomplete="new-password")
                submitted = st.form_submit_button("Create account", type="primary", width="stretch")
            if submitted:
                if pw != pw2:
                    st.error("The two passwords do not match.")
                else:
                    ok, msg, user = db.create_public_user(name, email, pw, phone)
                    if ok:
                        _finish_login(user)
                    st.error(msg)
        else:
            ui.html_block('<div class="auth-title">Log in</div>'
                          '<p class="auth-sub">New here? Choose Sign up above.</p>')
            with st.form("login_form"):
                email = st.text_input("Email", key="li_email", autocomplete="email")
                pw = st.text_input("Password", type="password", key="li_pw", autocomplete="current-password")
                submitted = st.form_submit_button("Log in", type="primary", width="stretch")
            if submitted:
                user = db.authenticate_public(email, pw)
                if user:
                    _finish_login(user)
                st.error("The email or password is not correct. Check them and try again, or sign up if you are new.")


def set_staff_mode(mode):
    ss["staff_mode"] = mode


def render_authority_login():
    mode = ss.get("staff_mode", "admin")
    left, right = st.columns([5, 6], gap="large")
    with left:
        ui.html_block(ui.auth_side(
            "Staff login",
            "For the main admin and for each Mangaluru department.",
            ["Main admin: see every department and approve solved complaints",
             "Department: see and update only your own department's complaints",
             "Residents see your updates when they track their complaint"]))
    with right, st.container(key="authcard"):
        with st.container(key="authtabs"):
            a, b = st.columns(2, gap="small")
            a.button("Main admin", key="tab_admin", type="primary" if mode == "admin" else "tertiary",
                     width="stretch", on_click=set_staff_mode, args=("admin",))
            b.button("Department", key="tab_dept", type="primary" if mode == "department" else "tertiary",
                     width="stretch", on_click=set_staff_mode, args=("department",))
        found, submitted = None, False
        if mode == "admin":
            ui.html_block('<div class="auth-title">Main admin login</div>'
                          '<p class="auth-sub">Use the admin username and password.</p>')
            with st.form("admin_form"):
                username = st.text_input("Username", key="au_user", autocomplete="username")
                password = st.text_input("Password", type="password", key="au_pw", autocomplete="current-password")
                submitted = st.form_submit_button("Log in", type="primary", width="stretch")
            if submitted:
                found = db.authenticate(username, password)
                if found and found["role"] != "admin":
                    found = None   # department accounts must use the Department tab
        else:
            ui.html_block('<div class="auth-title">Department login</div>'
                          '<p class="auth-sub">Choose your department and enter its password.</p>')
            names = {DEPTS[c][0]: c for c in DEPTS}
            with st.form("dept_form"):
                dept = st.selectbox("Department", list(names), key="dp_name")
                password = st.text_input("Password", type="password", key="dp_pw", autocomplete="current-password")
                submitted = st.form_submit_button("Log in", type="primary", width="stretch")
            if submitted:
                found = db.authenticate_department(names[dept], password)
        if found:
            ss["user"] = found
            ss["pub_user"] = None
            ss["apage"] = "overview"
            ss["page"] = "authority"
            st.rerun()
        if submitted:
            st.error("The login details are not correct. Check them and try again.")


# ------------------------------------------------------------------ report a complaint


def render_report():
    user = ss["pub_user"]
    ui.html_block(ui.page_head("Report a civic problem",
                               "Tell us where it is and what is wrong. Your complaint goes straight to the right department."))
    form_col, tips_col = st.columns([3, 2], gap="large")
    with tips_col:
        ui.html_block(ui.tips("Make your report easy to act on", [
            "Name the street or a nearby landmark.",
            "Say what is wrong and how long it has been like this.",
            "Mention who it affects: traffic, children, shops, homes.",
            "In an emergency, call 112 instead of using this form."]))
    with form_col:
        done_slot = st.container()
        with st.container(key="formcard"):
            with st.form("report_form", clear_on_submit=True):
                area = st.selectbox("Area", list(COORDS))
                category = st.selectbox("Category", list(DEPTS))
                text = st.text_area("Describe the problem", max_chars=1000, height=170)
                submitted = st.form_submit_button("Submit complaint", type="primary")
        if submitted:
            if not text.strip():
                st.warning("Please describe the problem first.")
            else:
                emotion, intensity = analyze_text(text.strip())
                cid = db.create_complaint(text.strip(), area, category, emotion, intensity, user_id=user["id"])
                ss["just_reported"] = {"id": cid, "dept": DEPTS[category][0]}
        done = ss.get("just_reported")
        if done:
            with done_slot:
                ui.html_block(ui.reported_card(done["id"], done["dept"]))
                st.code(done["id"], language=None)
                st.button("Track this complaint", key="track_now", type="primary", on_click=go,
                          args=("track",), kwargs={"tracked_id": done["id"], "track_id_input": done["id"]})


# ------------------------------------------------------------------ track your complaint


def render_track():
    user = ss["pub_user"]
    ui.html_block(ui.page_head("Track your complaint",
                               "Enter the complaint ID you received when you reported the problem."))
    with st.container(key="trackcard"):
        with st.form("track_form"):
            cid_in = st.text_input("Complaint ID", key="track_id_input", placeholder="For example 1122-093015-7C")
            clicked = st.form_submit_button("Track complaint", type="primary")
    if clicked:
        ss["tracked_id"] = (cid_in or "").strip()

    tid = ss.get("tracked_id")
    if tid:
        # Ownership is enforced in SQL: another citizen's ID looks exactly like an unknown ID.
        complaint = db.get_user_complaint(user["id"], tid)
        if complaint is None:
            st.error("No complaint with that ID was found in your account. Check the ID and try again.")
        else:
            dept = DEPTS.get(complaint["category"], DEPTS["Other"])[0]
            ui.html_block(ui.complaint_result(complaint, dept, db.get_complaint_log(complaint["id"])))

    mine = db.get_user_complaints(user["id"])
    ui.html_block('<div class="mine-title">Your complaints</div>')
    if mine.empty:
        ui.html_block('<div class="empty">You have not reported anything yet. Your complaints will be listed here.</div>')
        st.button("Report a complaint", key="track_empty_report", type="primary", on_click=go, args=("report",))
    else:
        ui.html_block(ui.my_complaints_table(mine))


# ------------------------------------------------------------------ router


def render():
    # Pages that need a login send visitors to the login page; signed-in citizens skip login pages.
    page = ss.get("page", "home")
    if page in ("report", "track") and not ss.get("pub_user"):
        page = ss["page"] = "auth_public"
        ss.setdefault("auth_mode", "login")
    if page in ("auth_public", "auth_authority") and ss.get("pub_user"):
        page = ss["page"] = "home"
    if page not in ("home", "report", "track", "auth_public", "auth_authority"):
        page = ss["page"] = "home"

    topbar()
    {"home": render_home, "report": render_report, "track": render_track,
     "auth_public": render_auth, "auth_authority": render_authority_login}[page]()
