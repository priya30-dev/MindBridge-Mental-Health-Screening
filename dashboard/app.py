"""MindBridge dashboard. Run with:  streamlit run dashboard/app.py"""

import streamlit as st

st.set_page_config(page_title="MindBridge", page_icon="🌿", layout="wide")

import ui  # noqa: E402  (after set_page_config)

ui.html(ui.THEME_CSS)

if not st.session_state.get("token"):
    pages = [st.Page("views/login.py", title="welcome", default=True)]
else:
    user = ui.current_user()
    pages = {
        "": [
            st.Page("views/checkin.py", title="check-in", icon=":material/favorite:", default=True),
            st.Page("views/chill.py", title="chill zone", icon=":material/spa:"),
            st.Page("views/journal.py", title="journal", icon=":material/menu_book:"),
            st.Page("views/report.py", title="my report", icon=":material/insights:"),
            st.Page("views/checkup.py", title="check-up quiz", icon=":material/checklist:"),
        ],
        "support": [
            st.Page("views/support.py", title="get support now", icon=":material/call:"),
            st.Page("views/settings.py", title="settings & privacy", icon=":material/settings:"),
        ],
    }
    if user.get("role") == "counsellor":
        pages["counsellor"] = [st.Page("views/counsellor.py", title="flagged check-ins", icon=":material/shield_person:")]

    with st.sidebar:
        ui.html(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
        <svg width="30" height="30" viewBox="0 0 34 34" aria-hidden="true"><circle cx="13" cy="17" r="11" fill="#CFC3FF"></circle><circle cx="21" cy="17" r="11" fill="#BFF0D9" fill-opacity="0.85"></circle></svg>
        <span class="mb-display" style="font-weight:800;font-size:1.35rem">mindbridge</span></div>
        <div class="mb-kicker">hey {ui.esc(user.get('display_name', ''))}</div>""")

nav = st.navigation(pages)

if st.session_state.get("token"):
    with st.sidebar:
        st.divider()
        ui.html('<div style="font-size:.85rem;color:#5B5670">need someone right now?<br><b style="color:#1E1B2E">Tele-MANAS 14416</b> · free, 24x7</div>')
        if st.button("log out", use_container_width=True):
            ui.logout()
            st.rerun()

nav.run()
