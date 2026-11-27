from datetime import date

import plotly.graph_objects as go
import streamlit as st
import ui

top_l, top_r = st.columns([2, 1])
with top_r:
    period = st.segmented_control("period", ["week", "month", "3 months"], default="month", label_visibility="collapsed")
days = {"week": 7, "month": 30, "3 months": 90}.get(period or "month", 30)
r = ui.safe_api("GET", f"/report?days={days}")
if not r:
    st.stop()

with top_l:
    title = f"your {date.today().strftime('%B').lower()}, wrapped" if days == 30 else f"your last {days} days, wrapped"
    ui.page_header(title, kicker=f"wellness report · {r['period']['from']} → {r['period']['to']}")

if r["checkin_count"] == 0:
    ui.card("nothing to wrap yet", "do a few check-ins and your report will fill up with trends, patterns and what helps you.", tone="lav")
    st.page_link("views/checkin.py", label="do a check-in →")
    st.stop()

delta = ""
if r["avg_risk"] is not None and r["prev_avg_risk"] is not None:
    d = r["avg_risk"] - r["prev_avg_risk"]
    delta = f"{'down' if d < 0 else 'up'} {abs(d):.0f} from the period before"
best = r.get("best_day")
tiles = [
    ("check-ins", r["checkin_count"], f"{r['voice_checkins']} with voice", "lav"),
    ("average stress", f"{r['avg_risk']:.0f}" if r["avg_risk"] is not None else "–", delta or "first period tracked", "mint"),
    ("calm minutes", r["calm_minutes"], "breathing + sounds", "butter"),
    ("best day", date.fromisoformat(best["date"]).strftime("%d %b").lower() if best else "–",
     f"stress {best['risk']:.0f}" if best else "", "sky"),
]
for col, (label, value, sub, tone) in zip(st.columns(4), tiles):
    with col:
        ui.html(f'<div class="mb-card mb-{tone}"><div class="mb-kicker" style="color:inherit">{label}</div>'
                f'<div class="mb-big">{ui.esc(value)}</div><div style="font-size:.85rem">{ui.esc(sub)}</div></div>')

with st.container(border=True):
    st.subheader("your stress over time")
    xs = [d["date"] for d in r["daily"]]
    ys = [d["risk"] for d in r["daily"]]
    fig = go.Figure()
    fig.add_hrect(y0=30, y1=60, fillcolor="#FFF6CC", opacity=0.6, line_width=0)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color="#6D4AFF", width=3, shape="spline"),
                             marker=dict(size=7), fill="tozeroy", fillcolor="rgba(207,195,255,0.25)",
                             hovertemplate="%{x}: stress %{y:.0f}<extra></extra>"))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(range=[0, 100], gridcolor="#F0ECFA", title="stress"),
                      xaxis=dict(showgrid=False), showlegend=False, font=dict(family="Inter", color="#4A4560"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("yellow band = medium zone (30–60)")

c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    if r["mood_mix"]:
        bar = "".join(f'<span style="width:{m["pct"]}%;background:{ui.MOODS[m["mood"]]["bar"]}"></span>' for m in r["mood_mix"])
        legend = "".join(ui.chip(f'{m["mood"]} · {m["pct"]}%', ui.MOODS[m["mood"]]["bg"], ui.MOODS[m["mood"]]["fg"]) for m in r["mood_mix"])
        ui.html(f'<div class="mb-card mb-white"><h3>your mood mix</h3><div style="display:flex;height:18px;border-radius:999px;overflow:hidden;margin:10px 0">{bar}</div>{legend}</div>')
    else:
        ui.card("your mood mix", "pick a vibe during check-ins to see this.", tone="white")
with c2:
    words = "".join(ui.chip(f'{w["word"]} · {w["count"]}×', "#FFE3D6", "#7A2E0B") for w in r["top_words"]) \
        or '<span style="color:#5B5670">turn on "show me which words mattered" during check-ins to see this.</span>'
    ui.html(f'<div class="mb-card mb-white"><h3>what weighed on you</h3><p style="color:#5B5670;font-size:.85rem;margin-bottom:8px">words that pushed your score up most often</p>{words}</div>')
with c3:
    names = {"breathing": "box breathing", "sound": "soundscapes", "release": "worries released", "grounding": "grounding", "affirmation": "reminders"}
    rows = "".join(f'<div style="display:flex;justify-content:space-between;margin:6px 0"><span>{names.get(k, k)}</span><b style="color:#0F6B4A">{v}×</b></div>'
                   for k, v in r["activities"].items())
    rows += f'<div style="display:flex;justify-content:space-between;margin:6px 0"><span>journal entries</span><b style="color:#0F6B4A">{r["journal_entries"]}</b></div>'
    insight = f'<p style="background:#EFFBF5;border-radius:12px;padding:10px 12px;margin-top:10px;font-size:.9rem;color:#0B4F37">{ui.esc(r["insight"])}</p>' if r.get("insight") else ""
    ui.html(f'<div class="mb-card mb-white"><h3>what helped</h3>{rows}{insight}</div>')

q1, q2 = st.columns([1.2, 1], gap="large")
with q1:
    qs = r.get("questionnaires") or {}
    if qs:
        names = {"phq9": ("PHQ-9 · mood", 27), "gad7": ("GAD-7 · anxiety", 21)}
        boxes = "".join(f'<div style="flex:1;background:#F7F4FF;border-radius:18px;padding:14px 16px"><div class="mb-kicker" style="color:#3F2C99">{names[k][0]}</div>'
                        f'<div class="mb-big" style="font-size:2rem;color:#2E1A8F">{q["score"]} <span style="font-size:1rem">/ {names[k][1]} · {ui.esc(q["severity"])}</span></div>'
                        f'<div style="font-size:.8rem;color:#4A4560">taken {q["date"]}</div></div>' for k, q in qs.items())
        ui.html(f'<div class="mb-card mb-white"><h3>check-up questionnaires</h3><div style="display:flex;gap:12px;margin-top:8px">{boxes}</div></div>')
    else:
        ui.card("check-up questionnaires", "take the 2-minute PHQ-9 and GAD-7 to add them to your report.", tone="white")
    st.page_link("views/checkup.py", label="take / retake the check-up →")
with q2:
    with st.container(border=True):
        st.subheader("download or share")
        pdf = None
        try:
            pdf = ui.api("GET", f"/report/pdf?days={days}", raw=True)
        except ui.ApiError as e:
            st.caption(f"pdf unavailable: {e}")
        if pdf:
            st.download_button("download pdf", data=pdf, file_name=f"mindbridge-report-{date.today()}.pdf",
                               mime="application/pdf", use_container_width=True, type="primary")
        user = ui.current_user()
        share = st.toggle("let my college counsellor see high-stress check-ins", value=user.get("share_with_counsellor", False),
                          help="they see a nickname, scores and dates — never your words or email")
        if share != user.get("share_with_counsellor", False):
            u = ui.safe_api("PATCH", "/auth/me", json={"share_with_counsellor": share})
            if u:
                st.session_state.user = u
                st.toast("updated")
st.caption(r["disclaimer"])
