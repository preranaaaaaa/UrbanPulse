"""UrbanPulse portal. Run from the project root:  streamlit run app/portal.py"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.getcwd())

st.set_page_config(page_title="UrbanPulse | Mangaluru civic portal", page_icon="🏙️", layout="wide")

from app import authority, db, public, ui  # noqa: E402  (after set_page_config on purpose)


@st.cache_resource
def _boot():
    """Create the tables and seed demo staff accounts once per server start, not on every click."""
    db.init_db()
    return True


_boot()
ss = st.session_state
ss.setdefault("page", "home")
ss.setdefault("pub_user", None)
ss.setdefault("user", None)

ui.inject_css(public=True)   # one design for every page; staff and public both use the top bar
if ss["user"]:
    authority.render(ss["user"])
else:
    public.render()
