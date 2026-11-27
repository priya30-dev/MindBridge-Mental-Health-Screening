import json

import streamlit as st
import ui

ui.page_header("settings & privacy", kicker="you're in control")
user = ui.current_user()

left, right = st.columns(2, gap="large")
with left:
    with st.container(border=True):
        st.subheader("profile & support")
        with st.form("settings"):
            name = st.text_input("display name", user.get("display_name", ""))
            st.markdown("**trusted contact** — only used when *you* tap to message them")
            c_name = st.text_input("their name", user.get("trusted_contact_name") or "")
            c_phone = st.text_input("their phone (with country code, e.g. +91…)", user.get("trusted_contact_phone") or "")
            save_text = st.toggle("save my check-in words by default", value=user.get("save_text_default", True))
            share = st.toggle("let my college counsellor see high-stress check-ins (nickname + scores only)",
                              value=user.get("share_with_counsellor", False))
            if st.form_submit_button("save", type="primary"):
                u = ui.safe_api("PATCH", "/auth/me", json={
                    "display_name": name, "trusted_contact_name": c_name, "trusted_contact_phone": c_phone,
                    "save_text_default": save_text, "share_with_counsellor": share})
                if u:
                    st.session_state.user = u
                    st.success("saved")

with right:
    with st.container(border=True):
        st.subheader("your data")
        st.write("download everything mindbridge stores about you, or delete it all — forever.")
        data = None
        try:
            data = ui.api("GET", "/me/data/export")
        except ui.ApiError as e:
            st.caption(str(e))
        if data:
            st.download_button("download my data (json)", json.dumps(data, indent=2), file_name="mindbridge-my-data.json",
                               mime="application/json", use_container_width=True)
        st.divider()
        st.markdown("**delete my account**")
        confirm = st.text_input("type DELETE to confirm", key="del_confirm")
        if st.button("delete everything", disabled=confirm != "DELETE", use_container_width=True):
            if ui.safe_api("DELETE", "/me/data"):
                ui.logout()
                st.rerun()
    ui.card("how we protect you", "passwords are hashed · your words are never shown to counsellors · "
            "you can turn off saving words anytime · worries you 'let go' are never stored.", tone="mint")
