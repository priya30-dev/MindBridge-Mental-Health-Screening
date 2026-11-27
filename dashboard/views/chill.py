import time

import streamlit as st
import streamlit.components.v1 as components
import ui

ui.html("""<div style="display:flex;align-items:center;gap:20px;margin-bottom:10px">
<svg width="84" height="84" viewBox="0 0 96 96" role="img" aria-label="Mochi, the MindBridge buddy" style="animation:floaty 3s ease-in-out infinite">
<path d="M48 10c22 0 36 18 36 40s-14 36-36 36-36-14-36-36 14-40 36-40z" fill="#CFC3FF"></path>
<ellipse cx="34" cy="52" rx="4" ry="5" fill="#2E1A8F"></ellipse><ellipse cx="62" cy="52" rx="4" ry="5" fill="#2E1A8F"></ellipse>
<circle cx="26" cy="62" r="6" fill="#FFB8C9" fill-opacity="0.7"></circle><circle cx="70" cy="62" r="6" fill="#FFB8C9" fill-opacity="0.7"></circle>
<path d="M42 62c2 3 4 4 6 4s4-1 6-4" fill="none" stroke="#2E1A8F" stroke-width="2.5" stroke-linecap="round"></path></svg>
<div><span style="background:#FFFFFF;border:1.5px solid #ECE8F7;border-radius:16px 16px 16px 4px;padding:8px 14px;color:#3F2C99">mochi says: proud of you for showing up today.</span>
<h1 style="font-size:2.7rem;margin:10px 0 0 0">chill zone</h1>
<p style="color:#5B5670;margin:0">pick whatever feels good. no streaks, no scores, no pressure.</p></div></div>
<style>@keyframes floaty{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}</style>""")


def log(kind, detail=None, minutes=0.0):
    ui.safe_api("POST", "/comfort/activity", json={"kind": kind, "detail": detail, "minutes": round(minutes, 1)})


def timed_session(key, kind, label_start, label_stop, detail=None):
    start_key = f"{key}_start"
    if st.session_state.get(start_key) is None:
        if st.button(label_start, key=f"{key}_go", type="primary"):
            st.session_state[start_key] = time.time()
            st.rerun()
        return False
    mins = (time.time() - st.session_state[start_key]) / 60
    if st.button(label_stop, key=f"{key}_stop"):
        log(kind, detail, max(mins, 0.5))
        st.session_state[start_key] = None
        st.toast(f"nice — {max(mins, 0.5):.0f} calm minute(s) added to your report")
        st.rerun()
    return True


left, right = st.columns(2, gap="large")

with left:
    with st.container(border=True):
        st.subheader("breathe with the bubble")
        active = timed_session("breath", "breathing", "start breathing", "i'm done")
        components.html("""
        <div style="font-family:Inter,sans-serif;display:flex;flex-direction:column;align-items:center;gap:10px">
        <div style="width:250px;height:250px;display:flex;align-items:center;justify-content:center">
        <div id="b" style="width:220px;height:220px;border-radius:50%;background:#CFC3FF;box-shadow:0 0 0 18px #E2DAFF;
        display:flex;align-items:center;justify-content:center;transition:transform 4s ease-in-out;transform:scale(.7)">
        <span id="t" style="font:700 22px 'Bricolage Grotesque',Inter,sans-serif;color:#2E1A8F">ready?</span></div></div>
        <div id="s" style="color:#3F2C99;font-size:14px">in 4 · hold 4 · out 4 · hold 4</div></div>
        <script>
        const ACTIVE = __ACTIVE__;
        const b = document.getElementById('b'), t = document.getElementById('t'), s = document.getElementById('s');
        const steps = [['breathe in',1],['hold',1],['breathe out',.55],['hold',.55]];
        let i = 0;
        function tick(){ const [w, sc] = steps[i]; t.textContent = w; b.style.transform = 'scale(' + sc + ')'; i = (i + 1) % 4; }
        if (ACTIVE) { s.textContent = 'follow the bubble — 4 seconds each'; tick(); setInterval(tick, 4000); }
        </script>""".replace("__ACTIVE__", "true" if active else "false"), height=300)

with right:
    with st.container(border=True):
        st.subheader("sounds to zone out")
        st.caption("made live in your browser — mix as many as you like. headphones recommended.")
        timed_session("sound", "sound", "log a listening session", "stop & log it", detail="soundscape")
        components.html("""
        <div style="font-family:Inter,sans-serif;display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <button data-k="rain">soft rain</button><button data-k="ocean">ocean swell</button>
        <button data-k="fire">campfire crackle</button><button data-k="brown">deep brown noise</button>
        <button data-k="white">white noise</button><button data-k="stop" style="background:#FFFFFF;border:2px dashed #9FDFC2">stop all</button>
        <label style="grid-column:1/3;font-size:14px;color:#1F5C45;font-weight:600">volume <input id="v" type="range" min="0" max="1" step="0.05" value="0.5" style="width:70%"></label>
        </div>
        <style>button{min-height:52px;border:2px solid transparent;border-radius:18px;background:#C9F0DE;color:#0B4F37;font:600 15px Inter,sans-serif;cursor:pointer}
        button.on{background:#FFFFFF;border-color:#0F6B4A}</style>
        <script>
        let ctx, master; const playing = {};
        function noise(type){
          const len = 2 * ctx.sampleRate, buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
          let last = 0, b0=0,b1=0,b2=0;
          for (let i = 0; i < len; i++) { const w = Math.random()*2-1;
            if (type==='white') d[i] = w*0.4;
            else if (type==='brown') { last = (last + 0.02*w)/1.02; d[i] = last*3.5; }
            else { b0=0.99765*b0+w*0.0990460; b1=0.96300*b1+w*0.2965164; b2=0.57000*b2+w*1.0526913; d[i]=(b0+b1+b2+w*0.1848)*0.11; } }
          const src = ctx.createBufferSource(); src.buffer = buf; src.loop = true; return src;
        }
        function make(k){
          const g = ctx.createGain(); g.connect(master); let nodes = [];
          if (k==='rain'){ const n = noise('pink'), f = ctx.createBiquadFilter(); f.type='highpass'; f.frequency.value=900; n.connect(f).connect(g); n.start(); nodes=[n]; g.gain.value=0.9; }
          if (k==='ocean'){ const n = noise('brown'), lfo = ctx.createOscillator(), lg = ctx.createGain(); lfo.frequency.value=0.09; lg.gain.value=0.45;
            lfo.connect(lg).connect(g.gain); g.gain.value=0.55; n.connect(g); n.start(); lfo.start(); nodes=[n,lfo]; }
          if (k==='brown'){ const n = noise('brown'); n.connect(g); n.start(); nodes=[n]; g.gain.value=0.7; }
          if (k==='white'){ const n = noise('white'); n.connect(g); n.start(); nodes=[n]; g.gain.value=0.35; }
          if (k==='fire'){ const n = noise('brown'), f = ctx.createBiquadFilter(); f.type='lowpass'; f.frequency.value=500; n.connect(f).connect(g); n.start(); g.gain.value=0.5;
            const iv = setInterval(()=>{ if (Math.random()<0.5) return; const c = ctx.createBufferSource(), b = ctx.createBuffer(1, 600, ctx.sampleRate), cd = b.getChannelData(0);
              for (let i=0;i<600;i++) cd[i]=(Math.random()*2-1)*Math.pow(1-i/600,4); c.buffer=b; const cg=ctx.createGain(); cg.gain.value=0.2+Math.random()*0.5; c.connect(cg).connect(g); c.start(); }, 90);
            nodes=[n,{stop:()=>clearInterval(iv)}]; }
          return {g, nodes};
        }
        document.querySelectorAll('button').forEach(btn => btn.onclick = () => {
          if (!ctx) { ctx = new AudioContext(); master = ctx.createGain(); master.gain.value = document.getElementById('v').value; master.connect(ctx.destination); }
          const k = btn.dataset.k;
          if (k==='stop'){ Object.keys(playing).forEach(x=>{ playing[x].nodes.forEach(n=>n.stop()); playing[x].g.disconnect(); delete playing[x]; });
            document.querySelectorAll('button.on').forEach(b=>b.classList.remove('on')); return; }
          if (playing[k]) { playing[k].nodes.forEach(n=>n.stop()); playing[k].g.disconnect(); delete playing[k]; btn.classList.remove('on'); }
          else { playing[k] = make(k); btn.classList.add('on'); }
        });
        document.getElementById('v').oninput = e => { if (master) master.gain.value = e.target.value; };
        </script>""", height=260)

c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    if "aff" not in st.session_state:
        st.session_state.aff = (ui.safe_api("GET", "/comfort/affirmation") or {}).get("text", "rest is productive too.")
    ui.card(st.session_state.aff, "", tone="butter", kicker="a little reminder")
    a1, a2 = st.columns(2)
    if a1.button("another one", use_container_width=True):
        st.session_state.aff = (ui.safe_api("GET", "/comfort/affirmation") or {}).get("text", st.session_state.aff)
        st.rerun()
    if a2.button("save to my kit", use_container_width=True):
        kit = list(ui.current_user().get("comfort_kit") or [])
        if st.session_state.aff not in kit:
            kit.append(st.session_state.aff)
            u = ui.safe_api("PATCH", "/auth/me", json={"comfort_kit": kit[-20:]})
            if u:
                st.session_state.user = u
                st.toast("saved to your comfort kit")

with c2:
    ui.card("let it go", "type one worry, then release it. it's never saved.", tone="peach")
    with st.form("release", clear_on_submit=True):
        worry = st.text_input("worry", placeholder="what if i fail tomorrow…", label_visibility="collapsed")
        if st.form_submit_button("release it", use_container_width=True) and worry.strip():
            log("release")
            st.session_state.released = st.session_state.get("released", 0) + 1
            st.session_state.last_worry = worry.strip()[:80]
    if st.session_state.get("last_worry"):
        ui.html(f"""<div style="position:relative;height:60px;overflow:hidden">
        <span style="position:absolute;left:0;right:0;text-align:center;color:#8F3A12;animation:away 3.5s ease-out forwards">{ui.esc(st.session_state.last_worry)}</span></div>
        <style>@keyframes away{{0%{{opacity:1;transform:translateY(30px)}}100%{{opacity:0;transform:translateY(-60px) scale(.8)}}}}</style>""")
        n = st.session_state.get("released", 0)
        st.caption("released. one less thing to carry." if n == 1 else f"{n} worries let go today.")
        st.session_state.last_worry = None

with c3:
    kit = list(ui.current_user().get("comfort_kit") or [])
    items = "".join(f'<div style="background:#FFFFFF;border-radius:14px;padding:9px 13px;margin-top:6px">{ui.esc(k)}</div>' for k in kit) \
        or '<div style="margin-top:6px;opacity:.8">nothing yet — add a song, a person, a place…</div>'
    ui.html(f'<div class="mb-card mb-sky"><h3>my comfort kit</h3><p>things that help you, saved for bad days.</p>{items}</div>')
    with st.form("kit", clear_on_submit=True):
        new = st.text_input("add", placeholder="call didi · chai on the balcony · my playlist", label_visibility="collapsed")
        k1, k2 = st.columns(2)
        add = k1.form_submit_button("+ add", use_container_width=True)
        clear = k2.form_submit_button("clear kit", use_container_width=True)
        if add and new.strip():
            kit.append(new.strip()[:80])
        if clear:
            kit = []
        if add or clear:
            u = ui.safe_api("PATCH", "/auth/me", json={"comfort_kit": kit[-20:]})
            if u:
                st.session_state.user = u
                st.rerun()

with st.expander("ground yourself · 5-4-3-2-1"):
    done = sum(st.checkbox(f"{n} {t}", key=f"g{n}") for n, t in
               [(5, "things you can see"), (4, "things you can touch"), (3, "things you can hear"),
                (2, "things you can smell"), (1, "thing you can taste")])
    if done == 5:
        st.success("you did it. breathe — you're here.")
        if not st.session_state.get("grounding_logged"):
            log("grounding", minutes=2)
            st.session_state.grounding_logged = True
