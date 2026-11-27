from collections import defaultdict
from datetime import date, datetime, timedelta

import streamlit as st
import ui

ui.page_header("mood journal", kicker="your space", subtitle="write it out. only you can see this unless you choose to share.")

left, right = st.columns([1.2, 1], gap="large")

with left:
    with st.container(border=True):
        st.subheader("new entry")
        prompt = st.selectbox("need a prompt?", [
            "just write freely",
            "right now i feel ___ because ___. one small thing i can do is ___.",
            "3 things that went okay today (not great, just okay)…",
            "what's taking up the most space in my head?",
            "what would i say to a friend feeling like this?",
        ])
        with st.form("entry", clear_on_submit=True):
            mood = st.pills("mood", list(ui.MOODS.keys()), selection_mode="single")
            content = st.text_area("entry", height=180, label_visibility="collapsed",
                                   placeholder="" if prompt == "just write freely" else prompt)
            analyse = st.toggle("let mindbridge track stress from this entry", value=True)
            if st.form_submit_button("save entry", type="primary", use_container_width=True):
                if not content.strip():
                    st.warning("write something first")
                else:
                    res = ui.safe_api("POST", "/journal", json={"content": content, "mood": mood, "analyse": analyse})
                    if res:
                        st.session_state.journal_saved = res
                        st.rerun()
    saved = st.session_state.pop("journal_saved", None)
    if saved:
        if saved.get("crisis_resources"):
            ui.crisis_banner(saved["crisis_resources"])
        else:
            st.toast("saved. proud of you for writing it down.")

with right:
    checkins = ui.safe_api("GET", "/checkins?days=7") or []
    by_day = defaultdict(list)
    for c in checkins:
        by_day[datetime.fromisoformat(c["created_at"]).date()].append(c["risk_score"])
    days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    bars = ""
    for d in days:
        vals = by_day.get(d)
        if vals:
            v = sum(vals) / len(vals)
            color = "#7FD9B0" if v < 30 else "#CFC3FF" if v < 50 else "#E8C64A" if v < 60 else "#F4A57F"
            bars += f'<div style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:6px;height:130px"><div title="{v:.0f}" style="width:100%;height:{max(v, 6):.0f}%;background:{color};border-radius:10px"></div><span style="font-size:.75rem;font-weight:600;color:#5B5670">{d.strftime("%a")[0]}</span></div>'
        else:
            bars += f'<div style="flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:6px;height:130px"><div style="width:100%;height:100%;border:2px dashed #DCD5F2;border-radius:10px;box-sizing:border-box"></div><span style="font-size:.75rem;font-weight:600;color:#5B5670">{d.strftime("%a")[0]}</span></div>'
    ui.html(f'<div class="mb-card mb-white"><h3>stress this week</h3><p style="color:#5B5670;font-size:.9rem">from your check-ins · dashed = no check-in</p>'
            f'<div style="display:flex;gap:8px;margin-top:12px">{bars}</div></div>')

st.subheader("recent entries")
entries = ui.safe_api("GET", "/journal?days=60") or []
if not entries:
    st.caption("no entries yet. your first one can be one sentence.")
for e in entries:
    m = ui.MOODS.get(e.get("mood") or "", {"bg": "#F4F1FC", "fg": "#4A4560"})
    when = datetime.fromisoformat(e["created_at"]).strftime("%a %d %b · %I:%M %p").lower()
    score = f'{e["risk_score"]:.0f}' if e.get("risk_score") is not None else "–"
    col_a, col_b = st.columns([12, 1])
    with col_a:
        ui.html(f'<div class="mb-card" style="background:{m["bg"]};color:{m["fg"]};display:flex;gap:14px;align-items:flex-start;padding:16px 18px">'
                f'<div style="flex:none;width:46px;height:46px;border-radius:14px;background:#FFFFFF;display:flex;align-items:center;justify-content:center;font:800 16px \'Bricolage Grotesque\',sans-serif">{score}</div>'
                f'<div><div style="font-size:.8rem;font-weight:600">{ui.esc(when)}{" · " + ui.esc(e["mood"]) if e.get("mood") else ""}</div>'
                f'<div style="white-space:pre-wrap;margin-top:2px">{ui.esc(e["content"])}</div></div></div>')
    with col_b:
        if st.button("✕", key=f"del{e['id']}", help="delete this entry"):
            ui.safe_api("DELETE", f"/journal/{e['id']}")
            st.rerun()
