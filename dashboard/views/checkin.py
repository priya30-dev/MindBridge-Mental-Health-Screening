from datetime import datetime

import streamlit as st
import ui

user = ui.current_user()
hour = datetime.now().hour
greet = "good morning" if hour < 12 else "hey" if hour < 18 else "evening"
ui.page_header(f"{greet} {user.get('display_name', '')}, how's your head today?",
               kicker="daily check-in · takes 1 min",
               subtitle="no right answers, no judgement. pick a vibe, then type, talk, or both.")

main, side = st.columns([1.75, 1], gap="large")

with main:
    with st.container(border=True):
        mood = st.pills("pick your vibe", list(ui.MOODS.keys()), selection_mode="single", key="mood")
        text = st.text_area("spill it — type, talk, or both", height=140, key="vent",
                            placeholder="ngl this week has been a lot… (english, hindi या hinglish — jo bhi comfortable ho)")
        voice = st.audio_input("add a voice note too (optional) — we notice energy, pace and tone, not just words")
        with st.expander("or upload an audio file instead"):
            upload = st.file_uploader("audio file", type=["wav", "mp3", "ogg", "flac", "m4a", "webm"], label_visibility="collapsed")
        c1, c2 = st.columns(2)
        explain = c1.toggle("show me which words mattered", value=True)
        save_text = c2.toggle("save my words to my history", value=user.get("save_text_default", True),
                              help="off = only scores are saved, never your words")
        go = st.button("vibe check →", type="primary", use_container_width=True)

    if go:
        audio_file = voice or upload
        if not text.strip() and audio_file is None:
            st.warning("type something or record a voice note first")
        else:
            files = None
            if audio_file is not None:
                name = getattr(audio_file, "name", None) or "voice.wav"
                files = {"audio": (name, audio_file.getvalue(), getattr(audio_file, "type", None) or "audio/wav")}
            data = {"text": text, "mood": mood or "", "explain": str(explain).lower(), "save_text": str(save_text).lower()}
            with st.spinner("listening closely…"):
                res = ui.safe_api("POST", "/checkins", data=data, files=files)
            if res:
                st.session_state.last_result = res

with side:
    tip = ui.safe_api("GET", "/comfort/affirmation") or {"text": "be gentle with yourself today."}
    ui.card(tip["text"], "", tone="butter", kicker="a little reminder")
    ui.card("1-min reset", "box breathing: in 4 · hold 4 · out 4 · hold 4", tone="mint", kicker="chill zone")
    st.page_link("views/chill.py", label="open chill zone →")
    ui.card("feeling like it's a lot?", "real humans are free to talk, 24x7. Tele-MANAS: <b>14416</b>", tone="peach")
    st.page_link("views/support.py", label="get support now →")

# ── RESULT ────────────────────────────────────────────────────────────────────
res = st.session_state.get("last_result")
if res:
    st.divider()
    when = "text + voice" if res.get("audio_score") is not None and res.get("text_score") is not None else (
        "voice" if res.get("audio_score") is not None else "text")
    ui.page_header("here's your vibe check", kicker=f"{when} check-in")

    if res.get("crisis_detected") or res["risk_score"] >= 80:
        ui.crisis_banner(res.get("crisis_resources"), res.get("suggest_contact"))
    if res.get("language_note"):
        st.info(res["language_note"])
    if res.get("trend_alert"):
        ui.card("we noticed a pattern", ui.esc(res["trend_alert"]), tone="peach")

    lv = ui.LEVELS.get(res["risk_level"], ui.LEVELS["MEDIUM"])
    headline = {"LOW": "you seem to be doing okay — love that for you.",
                "MEDIUM": "you're carrying a lot rn — and that's valid.",
                "HIGH": "this sounds really heavy. you deserve support.",
                "CRITICAL": "please don't sit with this alone."}[res["risk_level"]]

    r1, r2 = st.columns([1, 1.6], gap="large")
    with r1:
        ui.html(ui.stress_ring(res["risk_score"], res["risk_level"]))
        ui.html(f'<p class="mb-display" style="font-size:1.35rem;font-weight:800;color:{lv["fg"]};text-align:center">{headline}</p>'
                '<p style="text-align:center;color:#5B5670;font-size:.9rem">a screening signal, not a diagnosis.</p>')
    with r2:
        body = ""
        if res.get("analysed_text"):
            src = "from your voice note: " if res.get("transcript_used") else ""
            body += (f'<div style="background:#FCFBFF;border:1.5px solid #ECE8F7;border-radius:18px;padding:16px 18px;'
                     f'font-size:1.1rem;line-height:1.9;margin:10px 0">{ui.esc(src)}{ui.highlight(res["analysed_text"], res.get("top_tokens"))}</div>')
            if res.get("top_tokens"):
                body += ('<div style="font-size:.85rem;color:#5B5670;margin-bottom:10px">'
                         '<span class="mb-mark-up">peach</span> pushed stress up · <span class="mb-mark-down">mint</span> brought it down</div>')
        bars = ""
        voice_missing = res.get("voice") is not None and res.get("voice_model_ready") is False
        for label, val, fill, track in [("text signal", res.get("text_score"), "#6D4AFF", "#E4DDFF"),
                                        ("voice signal", res.get("audio_score"), "#1E9E6A", "#CDEFDF")]:
            shown = "not used" if val is None else f"{val:.0f}"
            if label == "voice signal" and voice_missing:
                shown = "coming soon"
            width = 0 if val is None else val
            bars += (f'<div style="flex:1;background:#F7F4FF;border-radius:16px;padding:12px 14px">'
                     f'<div style="display:flex;justify-content:space-between;font-weight:600;font-size:.9rem"><span>{label}</span><span>{shown}</span></div>'
                     f'<div class="mb-bar" style="background:{track};margin-top:8px"><div style="width:{width}%;background:{fill}"></div></div></div>')
        probs = res.get("probabilities")
        if probs:
            lang_names = {"en": "english", "hi": "hindi", "hinglish": "hinglish"}
            who = f' ({lang_names.get(res.get("language"), "")} → {res["model_used"]} model)' if res.get("model_used") else ""
            body += ('<div style="font-size:.85rem;color:#5B5670;margin-top:8px">model read: '
                     + " · ".join(f"{ui.esc(k.lower())} {v * 100:.0f}%" for k, v in probs.items())
                     + ui.esc(who) + "</div>")
        voice_html = ""
        v = res.get("voice")
        if v:
            if v.get("baseline_ready"):
                chips = "".join(ui.chip(c["label"], "#FFF1EA" if c["direction"] == "risk-increasing" else "#EFFBF5",
                                        "#8F3A12" if c["direction"] == "risk-increasing" else "#0F6B4A") for c in v["cues"])
                voice_html = f'<div style="margin-top:12px"><b style="font-size:.9rem">how you sounded:</b> {chips}</div>'
            else:
                voice_html = (f'<p style="margin-top:12px;font-size:.9rem;color:#5B5670">learning what your voice usually sounds like '
                              f'({v["baseline_count"]}/3 voice notes) — after that we can tell you how today compares.</p>')
        ui.html(f'<div class="mb-card mb-white"><h3>what we picked up on</h3>'
                f'<p style="color:#5B5670">text counts 65%, voice 35% when you use both.</p>{body}'
                f'<div style="display:flex;gap:12px;margin-top:8px">{bars}</div>{voice_html}</div>')

        fb = st.session_state.get(f"fb_{res['id']}")
        if fb:
            st.caption("thanks — this helps mindbridge get better.")
        else:
            f1, f2, f3 = st.columns([1.4, 1, 1])
            f1.markdown("**does this feel right?**")
            if f2.button("yep, kinda", key="fb_yes", use_container_width=True):
                ui.safe_api("POST", f"/checkins/{res['id']}/feedback", json={"feedback": "yes"})
                st.session_state[f"fb_{res['id']}"] = "yes"
                st.rerun()
            if f3.button("not really", key="fb_no", use_container_width=True):
                ui.safe_api("POST", f"/checkins/{res['id']}/feedback", json={"feedback": "no"})
                st.session_state[f"fb_{res['id']}"] = "no"
                st.rerun()

    ui.html('<h2 style="margin-top:10px">your next moves</h2>')
    m1, m2, m3 = st.columns(3)
    with m1:
        ui.card("breathe it out", "4 rounds of box breathing. your nervous system will thank you.", tone="mint")
        st.page_link("views/chill.py", label="start · 1 min →")
    with m2:
        ui.card("brain dump", "“right now i feel ___ because ___. one small thing i can do is ___.”", tone="lav")
        st.page_link("views/journal.py", label="open journal →")
    with m3:
        if res["risk_score"] >= 60:
            ui.card("talk to someone", "a counsellor or helpline can help you carry this. you don't need the perfect words.", tone="peach")
            st.page_link("views/support.py", label="see who to call →")
        else:
            ui.card("text your person", "“hey, rough week, can we talk?” is enough.", tone="sky")
            st.page_link("views/support.py", label="get a ready message →")
