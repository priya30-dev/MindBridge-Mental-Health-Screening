import re
from urllib.parse import quote

import streamlit as st
import ui

ui.html("""<div class="mb-card mb-peach" style="padding:34px">
<h1 style="font-size:2.6rem;margin:0 0 8px 0;color:#3D1A08">hey, we're really glad you're here.</h1>
<p style="font-size:1.1rem;color:#6B3418">if things feel heavy, you don't have to carry it alone. talking to a real person can make a difference — it's free and confidential.</p></div>""")

for col, h in zip(st.columns(3), ui.HELPLINES):
    with col:
        cls = "mb-tel" if h["tel"] == "14416" else "mb-tel soft"
        ui.html(f'<div class="mb-card mb-white" style="border-color:#F4BFA6"><div class="mb-kicker" style="color:#8F3A12">{ui.esc(h["hours"])}</div>'
                f'<h3>{ui.esc(h["name"])}</h3><div class="mb-big" style="color:#3D1A08">{ui.esc(h["contact"])}</div>'
                f'<a class="{cls}" href="tel:{h["tel"]}">call now</a></div>')

left, right = st.columns(2, gap="large")
with left:
    with st.container(border=True):
        st.subheader("reach your person")
        st.caption("you don't need the perfect words. send this to someone you trust:")
        msg = st.text_area("message", "hey, i'm not doing okay right now. can you call me or come over?", label_visibility="collapsed")
        user = ui.current_user()
        phone = re.sub(r"[^\d]", "", user.get("trusted_contact_phone") or "")
        if phone:
            st.link_button(f"send to {user.get('trusted_contact_name') or 'my person'} on whatsapp",
                           f"https://wa.me/{phone}?text={quote(msg)}", type="primary", use_container_width=True)
        else:
            st.link_button("open whatsapp", f"https://wa.me/?text={quote(msg)}", use_container_width=True)
            st.caption("tip: add a trusted contact in settings for one-tap sending.")
with right:
    with st.container(border=True):
        st.subheader("ground yourself · 5-4-3-2-1")
        done = sum(st.checkbox(f"{n} {t}", key=f"sg{n}") for n, t in
                   [(5, "things you can see"), (4, "things you can touch"), (3, "things you can hear"),
                    (2, "things you can smell"), (1, "thing you can taste")])
        st.caption("you did it. breathe — you're here." if done == 5 else f"{done} of 5 done")

st.caption("mindbridge is a screening tool, not a diagnosis. if you're in immediate danger, call 112 or go to the nearest hospital.")
