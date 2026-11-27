import pandas as pd
import streamlit as st
import ui

ui.page_header("flagged check-ins", kicker="counsellor view",
               subtitle="only students who opted in. you see a nickname, scores and dates — never their words or identity.")

c1, c2 = st.columns(2)
days = c1.slider("last N days", 1, 90, 14)
min_risk = c2.slider("minimum stress score", 0, 100, 60)
rows = ui.safe_api("GET", f"/counsellor/flagged?days={days}&min_risk={min_risk}") or []
if not rows:
    st.info("nothing flagged in this window.")
    st.stop()

df = pd.DataFrame(rows)
df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%d %b %H:%M")
df["crisis"] = df["crisis_detected"].map({True: "yes", False: ""})
edited = st.data_editor(
    df[["id", "student", "created_at", "risk_score", "risk_level", "crisis", "mood", "status"]],
    column_config={"status": st.column_config.SelectboxColumn("status", options=["new", "reviewed", "contacted", "resolved"]),
                   "id": None},
    disabled=["student", "created_at", "risk_score", "risk_level", "crisis", "mood"],
    hide_index=True, use_container_width=True)
if st.button("save status changes", type="primary"):
    changed = 0
    for orig, new in zip(rows, edited.to_dict("records")):
        if orig["status"] != new["status"]:
            ui.safe_api("PATCH", f"/counsellor/flagged/{orig['id']}", json={"status": new["status"]})
            changed += 1
    st.success(f"updated {changed} case(s)")
