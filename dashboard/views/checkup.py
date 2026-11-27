import streamlit as st
import ui

ui.page_header("check-up quiz", kicker="2 minutes each",
               subtitle="PHQ-9 and GAD-7 are short questionnaires doctors use worldwide. they're screening tools, not a diagnosis.")

tabs = st.tabs(["PHQ-9 · mood", "GAD-7 · anxiety"])
for tab, kind in zip(tabs, ["phq9", "gad7"]):
    with tab:
        q = ui.safe_api("GET", f"/questionnaires/{kind}")
        if not q:
            continue
        st.markdown(f"**{q['prompt']}**")
        labels = [o["label"] for o in q["options"]]
        with st.form(f"form_{kind}"):
            answers = []
            for i, item in enumerate(q["items"]):
                choice = st.radio(f"{i + 1}. {item}", labels, index=None, horizontal=True, key=f"{kind}_{i}")
                answers.append(labels.index(choice) if choice is not None else None)
            if st.form_submit_button("see my result", type="primary"):
                if None in answers:
                    st.warning("answer every question to see your result")
                else:
                    st.session_state[f"res_{kind}"] = ui.safe_api("POST", f"/questionnaires/{kind}", json={"answers": answers})
        res = st.session_state.get(f"res_{kind}")
        if res:
            if res.get("crisis_detected"):
                ui.crisis_banner(res.get("crisis_resources"))
            tone = {"minimal": "mint", "mild": "butter", "moderate": "peach"}.get(res["severity"], "peach")
            ui.html(f'<div class="mb-card mb-{tone}"><div class="mb-kicker" style="color:inherit">your score</div>'
                    f'<div class="mb-big">{res["score"]} <span style="font-size:1.1rem">/ {res["max"]} · {ui.esc(res["severity"])}</span></div>'
                    f'<p style="margin-top:6px">{ui.esc(res["advice"])}</p></div>')
            st.caption("saved to your report. retaking every 2 weeks helps you see change over time.")
