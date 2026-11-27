import streamlit as st
import ui

left, right = st.columns([1.1, 1], gap="large")

with left:
    ui.html("""<div style="padding-top:30px">
    <svg width="64" height="64" viewBox="0 0 34 34" aria-hidden="true"><circle cx="13" cy="17" r="11" fill="#CFC3FF"></circle><circle cx="21" cy="17" r="11" fill="#BFF0D9" fill-opacity="0.85"></circle></svg>
    <h1 style="font-size:3.4rem;line-height:1;margin:14px 0 10px 0">a soft place to check in with yourself.</h1>
    <p style="font-size:1.1rem;color:#5B5670;max-width:520px">type or voice-note how you're feeling. mindbridge spots stress early,
    shows you why, and gives you small things that actually help. private by default.</p>
    <div style="margin-top:16px">
    <span class="mb-chip" style="background:#EFEAFF;color:#4A2FC9">text + voice check-ins</span>
    <span class="mb-chip" style="background:#DDF7EC;color:#0F6B4A">chill zone</span>
    <span class="mb-chip" style="background:#FFF6CC;color:#6B4F00">monthly wrap</span>
    <span class="mb-chip" style="background:#FFE6DA;color:#8F3A12">real help, 24x7</span></div>
    <p style="font-size:.85rem;color:#5B5670;margin-top:24px">mindbridge is a screening tool, not a diagnosis.</p></div>""")

with right:
    with st.container(border=True):
        tab_in, tab_up = st.tabs(["log in", "create account"])
        with tab_in:
            with st.form("login"):
                email = st.text_input("email")
                pw = st.text_input("password", type="password")
                if st.form_submit_button("log in", type="primary", use_container_width=True):
                    res = ui.safe_api("POST", "/auth/login", json={"email": email, "password": pw})
                    if res:
                        st.session_state.token, st.session_state.user = res["token"], res["user"]
                        st.rerun()
        with tab_up:
            with st.form("register"):
                name = st.text_input("what should we call you?")
                email = st.text_input("email ")
                pw = st.text_input("password (8+ characters)", type="password")
                agree = st.checkbox("i understand mindbridge is a screening tool, not medical advice")
                if st.form_submit_button("create account", type="primary", use_container_width=True):
                    if not agree:
                        st.warning("please tick the box to continue")
                    else:
                        res = ui.safe_api("POST", "/auth/register", json={"email": email, "password": pw, "display_name": name})
                        if res:
                            st.session_state.token, st.session_state.user = res["token"], res["user"]
                            st.rerun()
