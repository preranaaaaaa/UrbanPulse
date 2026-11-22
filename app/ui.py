"""UrbanPulse design system: one stylesheet and the HTML pieces every page shares.

Colour: deep teal (the project identity) + marigold for highlights, on a pale sea-mist page.
Type:   Bricolage Grotesque for headings, Public Sans for reading text.
Rule:   all HTML goes through h() so Markdown never mistakes indented lines for a code block,
        and everything a user typed goes through esc() before it is placed in HTML.
"""
import html
from datetime import datetime

import streamlit as st

from app.constants import EMERGENCY

# ------------------------------------------------------------------ helpers


def h(markup):
    """Collapse an HTML snippet to one line (Markdown treats indented lines as code)."""
    return " ".join(line.strip() for line in markup.strip().splitlines() if line.strip())


def esc(value):
    return html.escape(str(value if value is not None else ""))


def esc_multiline(value):
    return esc(value).replace("\n", "<br>")


def fmt_ts(iso):
    """'2026-11-22T15:16:35' -> '22 Nov 2026, 3:16 pm' (works on Windows too)."""
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return esc(iso)
    return f"{d.day} {d:%b %Y}, {d.hour % 12 or 12}:{d:%M} {'am' if d.hour < 12 else 'pm'}"


def html_block(markup):
    st.markdown(h(markup), unsafe_allow_html=True)


# ------------------------------------------------------------------ stylesheet

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Public+Sans:wght@400;500;600;700&display=swap');

:root{
  --ink:#0C3B38; --teal:#0F766E; --teal-d:#0B5C56; --mist:#EDF3F1; --paper:#FFFFFF;
  --line:#D3DEDB; --field:#B4C5C1; --text:#1B2A29; --muted:#4F605E;
  --gold:#E6A23C; --gold-soft:#FBEFD6; --gold-ink:#7A4E00; --danger:#B42318; --ok:#1F7A4D;
  --display:'Bricolage Grotesque','Segoe UI',system-ui,sans-serif;
  --body:'Public Sans','Segoe UI',system-ui,-apple-system,sans-serif;
}

/* ---------- page ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"]{ background:var(--mist); color:var(--text); font-family:var(--body); }
.stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp [data-baseweb]{ font-family:var(--body); }
.stApp [data-testid="stMarkdownContainer"]{ font-family:var(--body); }
.stApp h1,.stApp h2,.stApp h3,.stApp h4{ font-family:var(--display); color:var(--ink); letter-spacing:-0.01em; }
.block-container, [data-testid="stMainBlockContainer"]{ max-width:1160px; padding:1.1rem 1.25rem 3rem; }
.stApp a{ color:var(--teal-d); }

/* ---------- keyboard focus ---------- */
.stApp button:focus-visible, .stApp a:focus-visible, .stApp input:focus-visible, .stApp textarea:focus-visible{
  outline:3px solid var(--gold) !important; outline-offset:2px; }

/* ---------- buttons ---------- */
.stApp button p{ color:inherit; font-weight:inherit; }
.stApp button[data-testid="stBaseButton-primary"], .stApp button[data-testid="stBaseButton-primaryFormSubmit"]{
  background:var(--teal); border:1px solid var(--teal); color:#fff; border-radius:10px; font-weight:600; min-height:2.75rem; padding:.45rem 1.2rem; }
.stApp button[data-testid="stBaseButton-primary"]:hover, .stApp button[data-testid="stBaseButton-primaryFormSubmit"]:hover{
  background:var(--teal-d); border-color:var(--teal-d); color:#fff; }
.stApp button[data-testid="stBaseButton-secondary"], .stApp button[data-testid="stBaseButton-secondaryFormSubmit"]{
  background:var(--paper); border:1px solid var(--field); color:var(--ink); border-radius:10px; font-weight:600; min-height:2.75rem; padding:.45rem 1.2rem; }
.stApp button[data-testid="stBaseButton-secondary"]:hover{ border-color:var(--teal); color:var(--teal-d); background:#F6FAF9; }
.stApp button[data-testid="stBaseButton-tertiary"]{
  background:transparent; border:1px solid transparent; color:var(--ink); border-radius:10px; font-weight:600; min-height:2.5rem; padding:.4rem .95rem; }
.stApp button[data-testid="stBaseButton-tertiary"]:hover{ background:var(--mist); color:var(--teal-d); }

/* ---------- form fields ---------- */
.stApp label p{ font-weight:600; color:var(--text); }
.stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"]{ background:#fff; border:1px solid var(--field); border-radius:10px; }
.stApp [data-baseweb="select"] > div{ background:#fff; border:1px solid var(--field); border-radius:10px; }
.stApp [data-baseweb="input"]:focus-within, .stApp [data-baseweb="textarea"]:focus-within{ border-color:var(--teal); }
.stApp [data-baseweb="tag"]{ background:var(--teal); color:#fff; border-radius:8px; }
.stApp [data-baseweb="tag"] span{ color:#fff; }
.stApp [data-baseweb="radio"] > div:first-child{ border-color:var(--teal); }
[data-testid="stForm"]{ border:none; padding:0; background:transparent; }

/* ---------- top bar ---------- */
.st-key-topbar{ background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:.55rem .9rem; margin-bottom:1.1rem; }
.st-key-topnav{ flex:1 1 auto; }
.brand{ display:flex; align-items:center; gap:.65rem; }
.brand svg{ width:34px; height:34px; flex:none; }
.brand-name{ font-family:var(--display); font-weight:800; font-size:1.3rem; color:var(--ink); letter-spacing:-0.02em; }
.brand-city{ font-size:.82rem; color:var(--muted); border-left:2px solid var(--gold); padding-left:.6rem; line-height:1.1; }

/* ---------- hero ---------- */
.hero{ background:var(--ink); color:#fff; border-radius:28px; padding:56px 52px 84px; display:grid; grid-template-columns:1.1fr .9fr; gap:44px; align-items:center; }
.hero h1{ color:#fff; font-size:clamp(2rem,4.2vw,3.35rem); line-height:1.06; font-weight:800; margin:0 0 18px; }
.hero p{ color:#D2E6E2; font-size:1.08rem; line-height:1.6; max-width:34rem; margin:0 0 14px; }
.hero .hero-note{ font-size:.95rem; color:#9FC4BE; margin:18px 0 0; }
.welcome{ background:var(--ink); color:#fff; border-radius:24px; padding:34px 40px; margin-bottom:1.4rem; }
.welcome h1{ color:#fff; font-size:clamp(1.6rem,3vw,2.3rem); margin:0 0 8px; font-weight:800; }
.welcome p{ color:#D2E6E2; margin:0; font-size:1.05rem; }

/* the complaint ticket: the one memorable object on the page */
.ticket{ background:#fff; color:var(--text); border-radius:20px; box-shadow:0 18px 40px rgba(0,0,0,.28); transform:rotate(1.2deg); max-width:400px; margin-left:auto; }
.ticket-top{ padding:22px 24px 18px; }
.ticket-label{ font-size:.8rem; color:var(--muted); font-weight:600; }
.ticket-id{ font-family:var(--display); font-weight:800; font-size:1.7rem; color:var(--ink); letter-spacing:.01em; margin:2px 0 10px; }
.ticket-text{ font-size:1rem; line-height:1.45; margin:0 0 12px; }
.chips{ display:flex; flex-wrap:wrap; gap:8px; }
.chip{ background:var(--mist); color:var(--ink); border-radius:999px; padding:3px 12px; font-size:.84rem; font-weight:600; }
.perf{ position:relative; border-top:2px dashed #C3D3CF; height:0; }
.perf::before,.perf::after{ content:""; position:absolute; top:-12px; width:22px; height:22px; border-radius:50%; background:var(--ink); }
.perf::before{ left:-11px; } .perf::after{ right:-11px; }
.ticket-bottom{ padding:20px 24px 18px; }
.ticket-tag{ font-size:.78rem; margin:14px 0 0; }
.hero .ticket-text{ color:var(--text); max-width:none; font-size:1rem; line-height:1.45; margin:0 0 12px; }
.hero .ticket-tag{ color:var(--muted); max-width:none; font-size:.8rem; margin:14px 0 0; }

/* status steps (ticket, track page) */
.steps{ display:flex; list-style:none; margin:0; padding:0; }
.steps li{ flex:1; position:relative; font-size:.88rem; font-weight:600; color:var(--muted); padding-top:30px; }
.steps li::before{ content:""; position:absolute; top:0; left:0; width:22px; height:22px; border-radius:50%; background:#fff; border:2px solid #B4C5C1; box-sizing:border-box; z-index:1; }
.steps li:not(:last-child)::after{ content:""; position:absolute; top:10px; left:26px; right:4px; height:2px; background:#D3DEDB; }
.steps li.done{ color:var(--ink); }
.steps li.done::before{ background:var(--teal); border-color:var(--teal); content:"\\2713"; color:#fff; font-size:.8rem; text-align:center; line-height:18px; }
.steps li.done:not(:last-child)::after{ background:var(--teal); }
.steps li.current{ color:var(--gold-ink); }
.steps li.current::before{ border-color:var(--gold); background:var(--gold); box-shadow:0 0 0 4px var(--gold-soft); }
.steps li.rejected{ color:var(--danger); }
.steps li.rejected::before{ background:var(--danger); border-color:var(--danger); content:"\\00D7"; color:#fff; text-align:center; line-height:18px; font-size:1rem; }

/* ---------- portal chooser (overlaps the hero) ---------- */
.st-key-portals{ margin-top:-52px; position:relative; z-index:3; padding:0 30px; }
.st-key-portal_public, .st-key-portal_authority{ background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:22px 26px 24px; box-shadow:0 10px 26px rgba(12,59,56,.10); }
.st-key-portal_public{ border-left:6px solid var(--teal); }
.st-key-portal_authority{ border-left:6px solid var(--gold); }
.portal-title{ font-family:var(--display); font-weight:800; font-size:1.35rem; color:var(--ink); margin:0 0 6px; }
.portal-text{ color:var(--muted); line-height:1.55; margin:0 0 14px; font-size:.98rem; }

/* ---------- sections ---------- */
.sec{ margin:3.1rem 0 1.2rem; }
.sec h2{ font-size:clamp(1.5rem,2.6vw,2rem); font-weight:800; margin:0 0 6px; }
.sec p{ color:var(--muted); margin:0; max-width:44rem; line-height:1.55; }

.flow{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }
.flow-step{ background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:22px 24px; }
.flow-num{ width:34px; height:34px; border-radius:50%; background:var(--gold-soft); color:var(--gold-ink); font-family:var(--display); font-weight:800; display:grid; place-items:center; margin-bottom:12px; }
.flow-step h3{ font-size:1.12rem; margin:0 0 6px; font-weight:700; }
.flow-step p{ margin:0; color:var(--muted); line-height:1.55; font-size:.97rem; }

.board{ background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:6px 28px; }
.board-row{ display:grid; grid-template-columns:230px 1fr; gap:24px; padding:18px 0; border-bottom:1px solid var(--line); }
.board-row:last-child{ border-bottom:none; }
.board-row b{ font-family:var(--display); font-size:1.05rem; color:var(--ink); }
.board-row span{ color:var(--text); line-height:1.6; }

.sos{ background:var(--gold-soft); border:1px solid #F0D49B; border-radius:18px; padding:22px 28px; margin-top:18px; display:flex; flex-wrap:wrap; gap:18px 32px; align-items:center; }
.sos-text{ flex:1 1 280px; }
.sos-text b{ font-family:var(--display); font-size:1.15rem; color:var(--gold-ink); display:block; margin-bottom:2px; }
.sos-text span{ color:#5B4210; }
.sos-nums{ display:flex; flex-wrap:wrap; gap:10px; }
.sos-nums a{ background:#fff; border:1px solid #E7C98A; border-radius:12px; padding:8px 16px; text-decoration:none; color:var(--ink); display:block; }
.sos-nums a b{ font-family:var(--display); font-size:1.35rem; display:block; line-height:1.1; }
.sos-nums a span{ font-size:.8rem; color:var(--muted); }

.depts{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
.dept{ background:var(--paper); border:1px solid var(--line); border-left:5px solid var(--teal); border-radius:14px; padding:18px 20px; }
.dept h3{ font-size:1.05rem; margin:0 0 2px; font-weight:700; }
.dept .for{ font-size:.85rem; color:var(--muted); margin:0 0 10px; }
.dept .row{ font-size:.95rem; line-height:1.75; word-break:break-word; }
.demo-note{ font-size:.85rem; color:var(--muted); margin-top:16px; }

.foot{ margin-top:3.2rem; padding-top:20px; border-top:1px solid var(--line); color:var(--muted); font-size:.9rem; line-height:1.6; }

/* ---------- sign up / log in ---------- */
.auth-side{ background:var(--ink); color:#fff; border-radius:24px; padding:38px 36px; }
.auth-side h1{ color:#fff; font-size:clamp(1.6rem,2.6vw,2.2rem); font-weight:800; margin:0 0 12px; line-height:1.12; }
.auth-side p{ color:#D2E6E2; line-height:1.6; margin:0 0 18px; }
.auth-side ul{ list-style:none; margin:0; padding:0; }
.auth-side li{ color:#fff; padding:9px 0 9px 28px; position:relative; line-height:1.5; border-top:1px solid #2B5A56; }
.auth-side li::before{ content:"\\2713"; position:absolute; left:0; color:var(--gold); font-weight:700; }
.st-key-authcard{ background:var(--paper); border:1px solid var(--line); border-radius:24px; padding:28px 30px 30px; }
.st-key-authtabs{ background:var(--mist); border-radius:12px; padding:4px; margin-bottom:6px; }
.auth-title{ font-family:var(--display); font-weight:800; font-size:1.5rem; color:var(--ink); margin:10px 0 4px; }
.auth-sub{ color:var(--muted); margin:0 0 6px; }

/* ---------- complaints: success, result, timeline ---------- */
.done-card{ background:var(--paper); border:1px solid var(--line); border-left:6px solid var(--ok); border-radius:16px; padding:22px 26px; margin-bottom:1.2rem; }
.done-card h3{ margin:0 0 4px; font-size:1.25rem; font-weight:800; }
.done-card p{ margin:0 0 6px; color:var(--muted); }
.done-id{ font-family:var(--display); font-weight:800; font-size:2rem; color:var(--ink); letter-spacing:.02em; margin:6px 0 2px; }
.result{ background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:24px 28px; margin-top:1rem; }
.result-head{ display:flex; flex-wrap:wrap; gap:10px 18px; align-items:center; justify-content:space-between; margin-bottom:6px; }
.result-id{ font-family:var(--display); font-weight:800; font-size:1.6rem; color:var(--ink); }
.result-meta{ color:var(--muted); font-size:.93rem; margin:0 0 16px; }
.result-text{ background:var(--mist); border-radius:12px; padding:14px 16px; margin:0 0 22px; line-height:1.6; }
.badge{ display:inline-block; border-radius:999px; padding:4px 14px; font-size:.86rem; font-weight:700; }
.badge.new{ background:#E1EBF5; color:#1F4E79; }
.badge.progress{ background:var(--gold-soft); color:var(--gold-ink); }
.badge.resolved{ background:#DDF1E6; color:#14633C; }
.badge.rejected{ background:#FBE4E1; color:#8F1D14; }
.tl-title{ font-family:var(--display); font-weight:700; font-size:1.05rem; margin:24px 0 10px; color:var(--ink); }
.tl{ list-style:none; margin:0; padding:0 0 0 6px; }
.tl li{ position:relative; padding:0 0 18px 26px; border-left:2px solid var(--line); margin-left:6px; }
.tl li:last-child{ border-left-color:transparent; padding-bottom:0; }
.tl li::before{ content:""; position:absolute; left:-8px; top:3px; width:14px; height:14px; border-radius:50%; background:var(--teal); border:3px solid #fff; box-shadow:0 0 0 1px var(--teal); }
.tl li b{ display:block; color:var(--ink); }
.tl li small{ color:var(--muted); }
.tl li span{ display:block; margin-top:2px; line-height:1.5; }
.empty{ background:var(--paper); border:1px dashed var(--field); border-radius:14px; padding:22px 24px; color:var(--muted); }
.mine-title{ font-family:var(--display); font-weight:800; font-size:1.3rem; color:var(--ink); margin:2.2rem 0 .6rem; }


/* ---------- inner pages ---------- */
.page-head{ margin:.6rem 0 1.3rem; }
.page-head h1{ font-size:clamp(1.7rem,3vw,2.4rem); font-weight:800; margin:0 0 6px; }
.page-head p{ color:var(--muted); margin:0; max-width:42rem; line-height:1.55; }
.st-key-formcard, .st-key-trackcard{ background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:26px 30px 28px; }
.tips{ background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:22px 26px; }
.tips h3{ font-size:1.1rem; margin:0 0 8px; font-weight:800; }
.tips ul{ margin:0; padding-left:1.1rem; color:var(--text); line-height:1.65; }
.tips li{ margin-bottom:6px; }
.table-wrap{ background:var(--paper); border:1px solid var(--line); border-radius:16px; overflow-x:auto; }
.mine{ width:100%; border-collapse:collapse; font-size:.95rem; min-width:560px; }
.mine th{ text-align:left; font-weight:600; color:var(--muted); font-size:.85rem; padding:12px 16px; border-bottom:1px solid var(--line); background:#F6FAF9; }
.mine td{ padding:13px 16px; border-bottom:1px solid var(--line); vertical-align:middle; }
.mine tr:last-child td{ border-bottom:none; }
.mine td.id{ font-family:var(--display); font-weight:800; color:var(--ink); white-space:nowrap; }


/* ---------- staff dashboards ---------- */
.who{ background:var(--gold-soft); color:var(--gold-ink); border-radius:999px; padding:6px 14px; font-size:.85rem; font-weight:700; white-space:nowrap; }
.kpis{ display:grid; grid-template-columns:1.6fr repeat(4,1fr); gap:14px; }
.kpi{ background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:18px 20px; }
.kpi b{ display:block; font-family:var(--display); font-size:2.1rem; line-height:1.05; color:var(--ink); font-weight:800; }
.kpi span{ color:var(--muted); font-size:.92rem; }
.kpi.total{ background:var(--ink); border-color:var(--ink); }
.kpi.total b{ color:#fff; font-size:3rem; }
.kpi.total span{ color:#C6DDD9; font-weight:600; }
.kpi.total small{ display:block; margin-top:10px; color:#9FC4BE; font-size:.9rem; line-height:1.5; }
.kpi.warn b{ color:var(--gold-ink); }
.alerts{ display:grid; gap:10px; margin-top:14px; }
.alert{ background:#FDECEA; border:1px solid #F1C2BC; border-left:6px solid var(--danger); border-radius:12px; padding:12px 18px; color:#5E1912; line-height:1.5; }
.alert b{ color:#8F1D14; }
.alert.gold{ background:var(--gold-soft); border-color:#F0D49B; border-left-color:var(--gold); color:#5B4210; }
.alert.gold b{ color:var(--gold-ink); }
.alert.calm{ background:#E8F4EE; border-color:#BFE0CE; border-left-color:var(--ok); color:#1B4D33; }
.legend{ display:flex; flex-wrap:wrap; gap:6px 18px; margin:2px 4px 12px; font-size:.88rem; color:var(--muted); }
.legend i{ display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:6px; vertical-align:-1px; }
.st-key-mapcard{ background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:16px 16px 12px; }
.st-key-mapcard iframe{ border-radius:12px; border:none; }
.prio{ display:inline-block; border-radius:6px; padding:2px 10px; font-weight:700; font-size:.82rem; }
.prio.high{ background:#FBE4E1; color:#8F1D14; }
.prio.med{ background:var(--gold-soft); color:var(--gold-ink); }
.prio.low{ background:#E1EBF5; color:#1F4E79; }
.prio.none{ background:var(--mist); color:var(--muted); }
.mine td.issue{ min-width:260px; max-width:380px; line-height:1.45; }
.mine td.issue small{ color:var(--muted); }
.how{ color:var(--muted); font-size:.88rem; margin:10px 2px 0; line-height:1.5; }
[class*="st-key-apv_"]{ background:var(--paper); border:1px solid #F0D49B; border-left:6px solid var(--gold); border-radius:16px; padding:18px 22px 14px; margin-bottom:12px; }
.approve{ margin:0; }
.approve .top{ display:flex; flex-wrap:wrap; gap:4px 14px; align-items:baseline; justify-content:space-between; }
.approve .top b{ font-family:var(--display); font-size:1.15rem; color:var(--ink); }
.approve .top span{ color:var(--muted); font-size:.9rem; }
.approve p{ margin:8px 0 0; line-height:1.55; }
.approve .dnote{ background:var(--gold-soft); border-radius:10px; padding:10px 14px; margin:10px 0 4px; color:#5B4210; }
.detail{ background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:20px 24px; margin:6px 0 10px; }
.detail-head{ display:flex; flex-wrap:wrap; gap:8px 16px; align-items:center; justify-content:space-between; }
.detail-head b{ font-family:var(--display); font-size:1.3rem; color:var(--ink); }
.detail .result-text{ margin:12px 0 0; }
.tl li small em{ font-style:normal; font-weight:600; color:var(--teal-d); }

/* ---------- small screens ---------- */
@media (max-width:860px){
  .hero{ grid-template-columns:1fr; padding:34px 26px 74px; gap:30px; }
  .ticket{ margin:0 auto; transform:none; }
  .flow, .depts{ grid-template-columns:1fr; }
  .board-row{ grid-template-columns:1fr; gap:4px; }
  .st-key-portals{ padding:0 8px; margin-top:-48px; }
  .welcome{ padding:26px 24px; }
  .kpis{ grid-template-columns:1fr 1fr; }
  .kpi.total{ grid-column:1 / -1; }
  .brand-city{ display:none; }
  .st-key-topbar{ flex-direction:column !important; align-items:flex-start !important; gap:.4rem !important; }
  .st-key-topnav{ width:100% !important; flex-direction:row !important; flex-wrap:wrap !important; justify-content:flex-start !important; gap:.25rem !important; }
  .st-key-topnav button{ padding:.3rem .7rem; min-height:2.2rem; font-size:.9rem; }
}
@media (prefers-reduced-motion:reduce){ *{ scroll-behavior:auto !important; transition:none !important; animation:none !important; } }
"""


def inject_css(public=True):
    """Add the theme. public=True also hides Streamlit's own header and the sidebar."""
    extra = ""
    if public:
        extra = """
        header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"],
        footer, #MainMenu { display:none !important; }
        """
    st.markdown(f"<style>{CSS}{extra}</style>", unsafe_allow_html=True)


# ------------------------------------------------------------------ pieces


def brand():
    return h("""
    <div class="brand">
      <svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#0F766E"/>
      <path d="M5 17h5l3-7 5 13 3-6h6" stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span class="brand-name">UrbanPulse</span><span class="brand-city">Mangaluru<br>civic portal</span>
    </div>""")


def stepper(status):
    """Progress steps for one complaint: Received, In progress, Resolved (or Rejected)."""
    if status == "Rejected":
        return h('<ol class="steps"><li class="done">Received</li><li class="rejected">Rejected</li></ol>')
    labels = ["Received", "In progress", "Resolved"]
    at = {"New": 0, "In progress": 1, "Resolved": 2}.get(status, 0)
    items = []
    for i, label in enumerate(labels):
        state = "done" if i < at or (i == at and status == "Resolved") else "current" if i == at else ""
        items.append(f'<li class="{state}">{label}</li>')
    return f'<ol class="steps">{"".join(items)}</ol>'


def badge(status):
    cls = {"New": "new", "In progress": "progress", "Pending approval": "progress", "Resolved": "resolved", "Rejected": "rejected"}.get(status, "new")
    return f'<span class="badge {cls}">{esc(status)}</span>'


def hero_guest():
    return h("""
    <section class="hero">
      <div>
        <h1>Report a civic problem. Follow it until it is fixed.</h1>
        <p>UrbanPulse sends your complaint to the right Mangaluru department, gives you a complaint ID,
        and shows every update until the work is done.</p>
        <p class="hero-note">Free for every resident. Your complaints are visible only to you and the department handling them.</p>
      </div>

      <div style="
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.14);
          border-radius: 18px;
          padding: 28px;
          align-self: center;
      ">
        <p style="
            color: #8edfd0;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 10px;
        ">From report to resolution</p>

        <h2 style="
            color: white;
            font-size: 25px;
            line-height: 1.3;
            margin: 0 0 22px 0;
        ">Every report helps make our city better.</h2>

        <div style="display: flex; gap: 14px; margin-bottom: 18px;">
          <div style="color: #8edfd0; font-size: 20px; font-weight: 700;">01</div>
          <div>
            <p style="color: white; font-weight: 600; margin: 0 0 4px 0;">Report the problem</p>
            <p style="color: #c4d1dc; font-size: 14px; margin: 0;">Share the location and details of the civic issue.</p>
          </div>
        </div>

        <div style="display: flex; gap: 14px; margin-bottom: 18px;">
          <div style="color: #8edfd0; font-size: 20px; font-weight: 700;">02</div>
          <div>
            <p style="color: white; font-weight: 600; margin: 0 0 4px 0;">Reach the right department</p>
            <p style="color: #c4d1dc; font-size: 14px; margin: 0;">Your report is routed to the team responsible for the issue.</p>
          </div>
        </div>

        <div style="display: flex; gap: 14px;">
          <div style="color: #8edfd0; font-size: 20px; font-weight: 700;">03</div>
          <div>
            <p style="color: white; font-weight: 600; margin: 0 0 4px 0;">Follow the updates</p>
            <p style="color: #c4d1dc; font-size: 14px; margin: 0;">Check your complaint's progress from your account.</p>
          </div>
        </div>
      </div>
    </section>
    """)

def welcome_banner(name, counts):
    total = sum(counts.values())
    if total == 0:
        line = "You have not reported anything yet. When you do, you will get a complaint ID to track it."
    else:
        open_n = counts.get("New", 0) + counts.get("In progress", 0)
        line = (f"You have reported {total} complaint{'s' if total != 1 else ''}: "
                f"{open_n} still open and {counts.get('Resolved', 0)} resolved.")
    return h(f'<section class="welcome"><h1>Welcome back, {esc(name)}</h1><p>{esc(line)}</p></section>')


def section(title, sub=None):
    sub_html = f"<p>{esc(sub)}</p>" if sub else ""
    return h(f'<div class="sec"><h2>{esc(title)}</h2>{sub_html}</div>')


def how_it_works():
    steps = [
        ("Sign up and log in", "Create a free account with your email. It keeps your complaints private to you."),
        ("Report the problem", "Pick your area and the type of problem, then describe it. You receive a complaint ID straight away."),
        ("Track it with your ID", "Enter the ID in Track your complaint to see its status and every action the department has taken."),
    ]
    cards = "".join(f'<div class="flow-step"><div class="flow-num">{i}</div><h3>{esc(t)}</h3><p>{esc(d)}</p></div>'
                    for i, (t, d) in enumerate(steps, 1))
    return h(f'<div class="flow">{cards}</div>')


def guidelines():
    rows = [
        ("Describe it clearly", "Name the street or a nearby landmark, say what is wrong and how long it has been like this, and mention who or what it affects."),
        ("One problem, one complaint", "Choose the category that fits best so it reaches the right department first time. File separate complaints for separate problems."),
        ("Keep your complaint ID", "You need it to track progress. Complaints you file are also listed under Track your complaint after you log in."),
        ("Keep drains and streets clear", "Keep wet and dry waste apart and never throw waste into storm drains. Blocked drains cause most monsoon waterlogging."),
        ("Stay safe around hazards", "Keep away from open manholes, fallen wires and flooded roads. Warn others, and report it here once you are safe."),
        ("Be respectful", "Complaints with abusive language, or with another person's private details, can be rejected."),
    ]
    body = "".join(f'<div class="board-row"><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in rows)
    return h(f'<div class="board">{body}</div>')


def emergency():
    nums = "".join(f'<a href="tel:{n}"><b>{n}</b><span>{esc(l)}</span></a>' for n, l in EMERGENCY)
    return h(f"""
    <div class="sos">
      <div class="sos-text"><b>In an emergency, call first</b>
      <span>Fire, a gas leak, a serious accident or anyone in danger needs a phone call, not a complaint form.</span></div>
      <div class="sos-nums">{nums}</div>
    </div>""")


def departments(depts):
    cards = []
    for cat, (name, head, phone, email) in depts.items():
        cards.append(
            f'<div class="dept"><h3>{esc(name)}</h3><p class="for">Handles {esc(cat.lower())} complaints</p>'
            f'<div class="row">Head: {esc(head)}<br>Phone: <a href="tel:{esc(phone)}">{esc(phone)}</a><br>'
            f'<a href="mailto:{esc(email)}">{esc(email)}</a></div></div>')
    return h(f'<div class="depts">{"".join(cards)}</div><p class="demo-note">These names and numbers are sample data for the demo.</p>')


def footer():
    return h('<div class="foot">UrbanPulse helps Mangaluru residents report civic problems and follow what happens next.<br>'
             'Complaints are shared only with the department responsible for them.</div>')


def auth_side(title, intro, points):
    items = "".join(f"<li>{esc(p)}</li>" for p in points)
    return h(f'<div class="auth-side"><h1>{esc(title)}</h1><p>{esc(intro)}</p><ul>{items}</ul></div>')


def reported_card(cid, dept):
    return h(f"""
    <div class="done-card">
      <h3>Complaint received</h3>
      <p>It has been sent to <b>{esc(dept)}</b>. Keep this ID safe. You need it to track your complaint.</p>
      <div class="done-id">{esc(cid)}</div>
    </div>""")


def complaint_result(c, dept, log):
    steps = "".join(
        f'<li><b>{esc(r.status)}</b><small>{fmt_ts(r.timestamp)}</small>'
        f'{"<span>" + esc_multiline(r.note) + "</span>" if isinstance(r.note, str) and r.note.strip() else ""}</li>'
        for r in log.itertuples())
    return h(f"""
    <div class="result">
      <div class="result-head"><div class="result-id">{esc(c["id"])}</div>{badge(c["status"])}</div>
      <p class="result-meta">{esc(c["category"])} in {esc(c["area"])}. Sent to {esc(dept)} on {fmt_ts(c["timestamp"])}.</p>
      <div class="result-text">{esc_multiline(c["text"])}</div>
      {stepper(c["status"])}
      <div class="tl-title">Updates</div>
      <ul class="tl">{steps}</ul>
    </div>""")


def page_head(title, sub=None):
    sub_html = f"<p>{esc(sub)}</p>" if sub else ""
    return h(f'<div class="page-head"><h1>{esc(title)}</h1>{sub_html}</div>')


def tips(title, items):
    lis = "".join(f"<li>{esc(i)}</li>" for i in items)
    return h(f'<div class="tips"><h3>{esc(title)}</h3><ul>{lis}</ul></div>')


def my_complaints_table(df, limit=50):
    """The citizen's own complaints. df must already be filtered to that citizen."""
    rows = "".join(
        f'<tr><td class="id">{esc(r.id)}</td><td>{fmt_ts(r.timestamp)}</td><td>{esc(r.category)}</td>'
        f'<td>{esc(r.area)}</td><td>{badge(r.status)}</td></tr>'
        for r in df.head(limit).itertuples())
    return h(f'''<div class="table-wrap"><table class="mine"><thead><tr><th>Complaint ID</th><th>Reported on</th>
    <th>Category</th><th>Area</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>''')
