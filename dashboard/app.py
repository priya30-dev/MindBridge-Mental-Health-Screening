import os
import requests
import streamlit as st
import plotly.graph_objects as go
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="MindBridge",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

for k, v in {
    "last_result": None, "show_help": False,
    "mood": "Calm", "mood_emoji": "😌",
    "journal_entries": [], "daily_tip": "",
    "breath_done": False, "selected_sample": "Choose sample →",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;1,500&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

:root{
  --bg:#F8F3EC; --card:#FEFCF8; --warm1:#F1E8DA; --warm2:#E4D3BC; --warm3:#CDB08A;
  --br1:#9C6B3C; --br2:#6B4220; --br3:#3D2308; --text:#271506; --muted:#6B4E35;
  --border:#DDD0BB; --ok:#2A5C38; --warn:#7A5200; --err:#8B1A1A;
  --ok-bg:#EDF7EE; --warn-bg:#FEF8E6; --err-bg:#FDF0F0;
  --shadow:0 4px 28px rgba(61,35,8,.09); --shadow2:0 2px 12px rgba(61,35,8,.06);
}

/* ── FULL SCREEN RESET ── */
#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="collapsedControl"],.stDeployButton,[data-testid="stStatusWidget"]{
  display:none!important;visibility:hidden!important;
}
html,body{margin:0!important;padding:0!important;background:var(--bg)!important;overflow-x:hidden!important;}
.stApp,[data-testid="stAppViewContainer"]{
  background:var(--bg)!important;
  width:100%!important;
  min-height:100vh!important;
}
[data-testid="stAppViewContainer"]>section:first-child{padding:0!important;}
.block-container{
  max-width:1440px!important;
  width:100%!important;
  padding:0 0 60px 0!important;
  margin:0 auto!important;
}
*{box-sizing:border-box;}

/* ── Typography ── */
h1,h2,h3,h4{font-family:'Playfair Display',serif!important;color:var(--br2)!important;font-weight:700!important;line-height:1.15!important;}
p,span,label,li,div{font-family:'DM Sans',sans-serif!important;color:var(--text)!important;}

/* ── TOPBAR ── */
.topbar{
  width:100%;background:var(--br3);
  padding:0 32px;height:58px;
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:0;
}
.t-logo{font-family:'Playfair Display',serif;font-size:21px;font-weight:700;color:#FAF6F0!important;letter-spacing:-.3px;}
.t-logo em{color:#CDB08A!important;font-style:italic;}
.t-nav{display:flex;gap:28px;font-size:13px;font-weight:500;}
.t-nav span{color:#E4D3BC!important;}

/* ── PAGE WRAPPER ── */
.pw{
  max-width:1360px;
  margin:0 auto;
  padding:0 32px;
}

/* ── HERO ── */
.hero{
  background:linear-gradient(130deg,#EDE0CC 0%,#FAF5ED 55%,#EAD9C8 100%);
  border:1px solid var(--border);border-radius:28px;
  padding:60px 56px;
  display:flex;align-items:center;justify-content:space-between;gap:40px;
  margin:28px 0 24px;box-shadow:var(--shadow);position:relative;overflow:hidden;
}
.hero::after{content:'';position:absolute;top:0;right:0;bottom:0;width:260px;
  background:radial-gradient(ellipse at right,rgba(205,176,138,.3),transparent 70%);pointer-events:none;}
.hero h1{font-size:50px!important;line-height:1.02!important;margin:0 0 14px!important;color:var(--br3)!important;}
.hero h1 em{color:var(--br1)!important;font-style:italic;}
.hero p{font-size:15px!important;max-width:580px;color:var(--muted)!important;margin:0!important;line-height:1.75!important;}
.hero-orb{width:170px;height:170px;min-width:170px;border-radius:50%;
  background:rgba(255,255,255,.55);border:1px solid var(--border);
  display:flex;align-items:center;justify-content:center;font-size:78px;
  box-shadow:var(--shadow);flex-shrink:0;position:relative;z-index:1;}
.hero-badges{display:flex;flex-wrap:wrap;gap:9px;margin-top:22px;}
.hb{background:rgba(255,255,255,.72);border:1px solid var(--border);color:var(--br1)!important;
  padding:6px 14px;border-radius:999px;font-size:12.5px;font-weight:600;}

/* ── ACTION CARDS ── */
.ac-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;}
.ac{background:linear-gradient(150deg,#FDFAF4,#F5EADC);border:1px solid var(--border);
  border-radius:20px;padding:22px 20px;box-shadow:var(--shadow2);}
.ac h4{font-size:16px!important;margin:0 0 7px!important;color:var(--br2)!important;}
.ac p{font-size:13px!important;color:var(--muted)!important;margin:0!important;line-height:1.6!important;}

/* ── CARD ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:22px;
  padding:26px 28px;box-shadow:var(--shadow2);margin-bottom:18px;}
.card-title{font-family:'Playfair Display',serif!important;font-size:19px!important;
  font-weight:700!important;color:var(--br2)!important;
  margin:0 0 15px!important;padding-bottom:11px;border-bottom:1px solid var(--warm2);line-height:1.2!important;}

/* ── MOOD CHIP ── */
.mood-chip{background:var(--warm1);border:1px solid var(--warm3);border-radius:14px;
  padding:12px 16px;text-align:center;font-weight:700;font-size:15px;
  color:var(--br2)!important;margin-top:12px;}

/* ── BUTTONS ── */
.stButton>button{
  background:var(--br1)!important;color:#fff!important;border:none!important;
  border-radius:14px!important;font-family:'DM Sans',sans-serif!important;
  font-weight:600!important;font-size:14px!important;min-height:44px!important;
  box-shadow:0 4px 14px rgba(156,107,60,.22)!important;transition:all .15s!important;
}
.stButton>button:hover{background:var(--br2)!important;transform:translateY(-1px)!important;}
.stButton>button:active{transform:scale(.98)!important;}

/* Mood buttons */
div[data-testid="column"] .stButton>button{
  background:#FDFAF4!important;color:var(--br2)!important;
  border:1.5px solid var(--border)!important;box-shadow:var(--shadow2)!important;
  min-height:88px!important;font-size:15px!important;
  white-space:pre-line!important;border-radius:18px!important;
}
div[data-testid="column"] .stButton>button:hover{
  background:var(--warm1)!important;border-color:var(--br1)!important;transform:translateY(-2px)!important;
}

/* ── INPUTS ── */
.stTextArea textarea,.stTextInput input{
  background:#FFFEF9!important;border:1.5px solid var(--border)!important;
  border-radius:14px!important;color:var(--text)!important;
  font-family:'DM Sans',sans-serif!important;font-size:14.5px!important;line-height:1.7!important;
}
.stTextArea textarea::placeholder,.stTextInput input::placeholder{color:#B8A090!important;}

/* ── DROPDOWN FIX — white background ── */
.stSelectbox [data-baseweb="select"]>div,
.stSelectbox [data-baseweb="select"] div,
[data-baseweb="popover"],[data-baseweb="menu"],
[data-baseweb="menu"] ul,[data-baseweb="menu"] li,
[role="listbox"],[role="option"]{
  background:#FFFEF9!important;
  color:var(--text)!important;
  font-family:'DM Sans',sans-serif!important;
}
[data-baseweb="select"] [data-baseweb="select"]>div{border:1.5px solid var(--border)!important;border-radius:14px!important;}
[role="option"]:hover,[data-baseweb="menu"] li:hover{background:var(--warm1)!important;color:var(--br2)!important;}
[role="option"] span,[data-baseweb="menu"] li span{color:var(--text)!important;}
[data-baseweb="popover"] div{background:#FFFEF9!important;border:1px solid var(--border)!important;border-radius:14px!important;}

/* ── Widget labels ── */
.stRadio label,.stCheckbox label,
[data-testid="stWidgetLabel"] p,div[data-testid="stWidgetLabel"]{
  color:var(--text)!important;font-weight:600!important;font-size:13.5px!important;
}

/* ── NOTICES ── */
.nb{border-radius:0 12px 12px 0;padding:10px 14px;font-size:13.5px!important;line-height:1.6;margin-bottom:10px;}
.nb.warn{background:var(--warn-bg);border-left:3px solid #C89A20;color:var(--warn)!important;}
.nb.err{background:var(--err-bg);border-left:3px solid #B83232;color:var(--err)!important;}
.nb.ok{background:var(--ok-bg);border-left:3px solid #3A8A50;color:var(--ok)!important;}

/* ── FLAGS ── */
.flag{display:flex;align-items:center;gap:10px;padding:12px 15px;border-radius:12px;margin-bottom:9px;font-size:13.5px;font-weight:600;}
.flag.high{background:var(--err-bg);border:1px solid #E0AAAA;color:var(--err)!important;}
.flag.med{background:var(--warn-bg);border:1px solid #E0C060;color:var(--warn)!important;}
.flag.low{background:var(--ok-bg);border:1px solid #90C09A;color:var(--ok)!important;}
.fdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}

/* ── SHAP TOKENS ── */
.tgrid{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;}
.tok{padding:7px 13px;border-radius:9px;font-size:13px;font-weight:600;font-family:'DM Mono',monospace;display:inline-flex;align-items:center;gap:5px;}
.tok.r{background:#FDF0F0;border:1px solid #E0AAAA;color:#8B1A1A!important;}
.tok.s{background:#EDF7EE;border:1px solid #90C09A;color:#2A5C38!important;}
.tval{font-size:10px!important;opacity:.65;}

/* ── CHALLENGE BOX ── */
.cbox{background:linear-gradient(135deg,var(--br3),#7A4A25);border-radius:24px;
  padding:28px 32px;margin:8px 0 18px;box-shadow:var(--shadow);}
.cbox h3{color:#FAF6F0!important;font-size:24px!important;margin:0 0 8px!important;}
.cbox p{color:#F1E5D8!important;font-size:14.5px!important;margin:0!important;line-height:1.7!important;}

/* ── PLAN GRID ── */
.plan-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px;}
.plan{background:var(--warm1);border:1px dashed var(--warm3);border-radius:18px;padding:18px;}
.plan b{color:var(--br2)!important;font-size:14.5px;}
.plan p{font-size:13px!important;color:var(--muted)!important;margin:7px 0 0!important;line-height:1.55!important;}

/* ── QUOTE ── */
.quote{background:var(--warm1);border-left:4px solid var(--br1);border-radius:0 14px 14px 0;
  padding:14px 18px;font-weight:600;font-size:14.5px;color:var(--br2)!important;margin:12px 0;font-style:italic;}

/* ── TODO GRID ── */
.todo-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;}
.todo{background:#FFFEF9;border:1px solid var(--border);border-radius:12px;padding:12px 14px;font-size:13.5px;color:var(--text)!important;line-height:1.5;}

/* ── METRICS ── */
.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px;}
.metric{background:var(--warm1);border:1px solid var(--border);border-radius:16px;padding:16px;text-align:center;}
.metric b{font-size:26px;color:var(--br2)!important;display:block;margin-bottom:4px;}
.metric p{font-size:12px!important;color:var(--muted)!important;margin:0!important;line-height:1.3!important;}

/* ── BREATHING ── */
.breath-orb{width:160px;height:160px;border-radius:50%;margin:18px auto;
  background:radial-gradient(circle,#F8F0E4,#EAD9C2);border:1.5px solid var(--warm3);
  display:flex;align-items:center;justify-content:center;font-size:52px;
  box-shadow:0 8px 32px rgba(156,107,60,.18);}

/* ── JOURNAL ── */
.journal-prompt{background:var(--warm1);border:1px solid var(--border);border-radius:14px;
  padding:14px 16px;font-size:14px;color:var(--br2)!important;font-style:italic;margin-bottom:12px;line-height:1.6;}
.j-entry{background:#FFFEF9;border:1px solid var(--border);border-radius:11px;padding:11px 13px;font-size:13.5px;margin-bottom:7px;color:var(--text)!important;}
.j-time{font-size:11px;color:var(--muted)!important;font-family:'DM Mono',monospace;margin-bottom:3px;}

/* ── MUSIC GRID ── */
.music-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px;}
.mcard{background:var(--warm1);border:1px solid var(--border);border-radius:16px;padding:16px;text-align:center;}
.mcard a{text-decoration:none!important;font-weight:700;font-size:14px;color:var(--br2)!important;}
.mcard p{font-size:12px!important;color:var(--muted)!important;margin:6px 0 0!important;}

/* ── RESOURCE GRID ── */
.res-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:28px 0 0;}
.res{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:20px 22px;box-shadow:var(--shadow2);}
.res h4{font-size:17px!important;margin:0 0 7px!important;color:var(--br2)!important;}
.res p{font-size:13px!important;color:var(--muted)!important;margin:0!important;line-height:1.6!important;}

/* ── PBAR ── */
.pbar-wrap{margin-bottom:10px;}
.pbar-row{display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted)!important;margin-bottom:4px;}
.pbar-track{background:var(--warm2);border-radius:999px;height:6px;overflow:hidden;}
.pbar-fill{height:100%;border-radius:999px;}

/* ── FOOTER ── */
.footer{text-align:center;color:var(--muted)!important;font-size:12px;
  padding:28px 0 10px;border-top:1px solid var(--warm2);margin-top:36px;font-family:'DM Mono',monospace;}

/* ── DIVIDER ── */
.div{height:1px;background:var(--warm2);margin:24px 0;}

/* ── HELP BOX ── */
.help-box{background:var(--card);border:1.5px solid var(--br1);border-radius:20px;padding:24px 28px;margin-bottom:20px;box-shadow:var(--shadow2);}

/* ── RESPONSIVE ── */
@media(max-width:1100px){
  .ac-grid{grid-template-columns:repeat(2,1fr)!important;}
}

@media(max-width:960px){
  .block-container{max-width:100%!important;}
  .pw{padding:0 16px!important;}
  .topbar{padding:0 16px!important;}
  .t-nav{display:none!important;}
  .hero{
    padding:32px 22px!important;
    flex-direction:column!important;
    text-align:left!important;
    align-items:flex-start!important;
  }
  .hero h1{font-size:38px!important;}
  .hero p{font-size:14px!important;}
  .hero-badges{gap:7px!important;}
  .hb{font-size:11.5px!important;padding:6px 10px!important;}
  .hero-orb{
    width:100px!important;height:100px!important;min-width:100px!important;
    font-size:46px!important;align-self:center!important;
  }
  .ac-grid,.plan-grid,.todo-grid,.music-grid,.metric-grid,.res-grid{grid-template-columns:1fr!important;}
  .card{padding:22px 18px!important;}
}

@media(max-width:520px){
  .topbar{height:54px!important;}
  .t-logo{font-size:18px!important;}
  .hero h1{font-size:34px!important;}
  .hero{border-radius:20px!important;margin:18px 0!important;}
  .ac{padding:18px 16px!important;}
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def set_mood(label, emoji):
    st.session_state.mood = label
    st.session_state.mood_emoji = emoji

def get_tip():
    tips = [
        "Drink a full glass of water before checking your phone.",
        "Take a 10-minute walk without your phone today.",
        "Write down 3 things that went okay — not great, just okay.",
        "Get 10–15 minutes of natural sunlight if possible.",
        "Text one safe person instead of isolating today.",
        "Sleep matters more than one extra hour of scrolling.",
        "Your mood right now is not your mood forever.",
        "Breathing slowly for 60 seconds actually works.",
    ]
    if not st.session_state.daily_tip:
        st.session_state.daily_tip = random.choice(tips)
    return st.session_state.daily_tip

def emotion_breakdown(score):
    return {
        "Stress":     min(95, max(8,  score + 12)),
        "Anxiety":    min(92, max(10, score - 3)),
        "Sadness":    min(90, max(6,  score - 8)),
        "Positivity": max(5,  100 - score),
    }

def wellness_score(risk): return max(0, min(100, 100 - int(risk)))

# ── FIXED demo result — uses SAMPLE KEY not text keywords ─────────────────────
SAMPLE_RESULTS = {
    "Choose sample →": None,
    "Low risk — peaceful day": {
        "risk_score": 9, "risk_level": "LOW", "risk_color": "#2A5C38",
        "flags": [], "text_score": 9, "audio_score": None,
        "top_tokens": [
            {"token": "peaceful", "shap_value": -0.31, "direction": "risk-reducing"},
            {"token": "grateful", "shap_value": -0.26, "direction": "risk-reducing"},
            {"token": "manageable", "shap_value": -0.19, "direction": "risk-reducing"},
        ],
        "disclaimer": "Algorithmic alert only — not a clinical diagnosis."
    },
    "Medium risk — overwhelmed": {
        "risk_score": 54, "risk_level": "MEDIUM", "risk_color": "#9A6A00",
        "flags": ["MONITORING_RECOMMENDED"], "text_score": 54, "audio_score": None,
        "top_tokens": [
            {"token": "overwhelmed", "shap_value": 0.61, "direction": "risk-increasing"},
            {"token": "tired", "shap_value": 0.41, "direction": "risk-increasing"},
            {"token": "cannot", "shap_value": 0.33, "direction": "risk-increasing"},
        ],
        "disclaimer": "Algorithmic alert only — not a clinical diagnosis."
    },
    "High risk — hopeless": {
        "risk_score": 89, "risk_level": "HIGH", "risk_color": "#8B1A1A",
        "flags": ["IMMEDIATE_REVIEW_REQUIRED", "CLINICAL_CONSULTATION_ADVISED"],
        "text_score": 89, "audio_score": None,
        "top_tokens": [
            {"token": "hopeless", "shap_value": 0.82, "direction": "risk-increasing"},
            {"token": "better off", "shap_value": 0.78, "direction": "risk-increasing"},
            {"token": "no point", "shap_value": 0.61, "direction": "risk-increasing"},
        ],
        "disclaimer": "Algorithmic alert only — not a clinical diagnosis."
    },
}

def demo_result_from_text(text):
    t = text.lower()
    if any(w in t for w in ["hopeless","without me","better off","die","end","no point","suicide"]):
        return SAMPLE_RESULTS["High risk — hopeless"]
    if any(w in t for w in ["overwhelmed","tired","exhausted","anxious","cannot","can't","stressed"]):
        return SAMPLE_RESULTS["Medium risk — overwhelmed"]
    return SAMPLE_RESULTS["Low risk — peaceful day"]


# ── TOPBAR ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div class="t-logo">🌿 Mind<em>Bridge</em></div>
  <div class="t-nav">
    <span>Screening</span><span>Resources</span><span>Privacy</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Page wrapper open
st.markdown('<div class="pw">', unsafe_allow_html=True)

# ── Help / Clear ──────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([11, 1])
with hc1:
    if st.button("❓  How to use MindBridge", use_container_width=True):
        st.session_state.show_help = not st.session_state.show_help
with hc2:
    if st.button("↺", use_container_width=True):
        st.session_state.last_result = None
        st.session_state.selected_sample = "Choose sample →"
        st.rerun()

if st.session_state.show_help:
    st.markdown('<div class="help-box">', unsafe_allow_html=True)
    hh1, hh2 = st.columns(2)
    with hh1:
        st.markdown("""
**Steps:**
1. Pick your current mood
2. Choose Text or Audio input
3. Select a sample OR type your own
4. Click Analyse
5. Read score, flags, and word highlights
        """)
    with hh2:
        st.markdown("""
**Risk levels:**
- 🟢 0–30 LOW — No immediate concern
- 🟡 30–60 MEDIUM — Monitor & follow up
- 🟠 60–80 HIGH — Clinical consultation
- 🔴 80–100 CRITICAL — Immediate review

🚨 **Emergency → Call 112 immediately**
        """)
    if st.button("Close ✕", key="close_help"):
        st.session_state.show_help = False
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div>
    <h1>Mental wellness<br><em>screening space</em></h1>
    <p>Analyse text or audio for early signals of stress, anxiety, and depression.
       Private by design, explainable by default, and built for thoughtful screening.</p>
    <div class="hero-badges">
      <span class="hb">🔒 No data stored</span>
      <span class="hb">📝 Text</span>
      <span class="hb">🎙 Audio</span>
      <span class="hb">⚡ Fast</span>
      <span class="hb">🔍 Explainable AI</span>
      <span class="hb">🧘 After-care plan</span>
    </div>
  </div>
  <div class="hero-orb">🌿</div>
</div>
""", unsafe_allow_html=True)

# ── ACTION CARDS ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="ac-grid">
  <div class="ac"><h4>🧠 Smart screening</h4>
    <p>Text, journal entries, chat messages, or audio notes — all analysed for emotional signals.</p></div>
  <div class="ac"><h4>🌱 After-care tools</h4>
    <p>Grounding, breathing, journaling, and personalised next-step cards follow every result.</p></div>
  <div class="ac"><h4>📊 Visual result</h4>
    <p>Risk gauge, confidence bars, flags, and SHAP word highlights in one clear layout.</p></div>
  <div class="ac"><h4>🔒 Private session</h4>
    <p>No login required. No data leaves your session. Results cleared when you close the tab.</p></div>
</div>
""", unsafe_allow_html=True)

# ── MOOD CHECK-IN ─────────────────────────────────────────────────────────────
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<p class="card-title">Mood check-in — how are you right now?</p>', unsafe_allow_html=True)
st.markdown('<p style="color:var(--muted);font-size:14px;margin:-8px 0 16px">Pick what matches your current state before screening.</p>', unsafe_allow_html=True)
mc = st.columns(5, gap="small")
for col, (emoji, label) in zip(mc, [("😌","Calm"),("😕","Low"),("😵‍💫","Stress"),("😟","Anxious"),("🤍","Numb")]):
    with col:
        if st.button(f"{emoji}\n\n{label}", key=f"m_{label}", use_container_width=True):
            set_mood(label, emoji)
st.markdown(f'<div class="mood-chip">Current mood: {st.session_state.mood_emoji} &nbsp;<b>{st.session_state.mood}</b></div>',
            unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── MAIN COLUMNS ──────────────────────────────────────────────────────────────
left, right = st.columns([0.38, 0.62], gap="large")

with left:
    st.markdown(f"""
    <div class="card">
      <p class="card-title">Before you begin</p>
      <div class="nb err">🚨 Emergency? Call <b>112</b> (India) immediately.</div>
      <div class="nb warn">Input sent only to your local API. Nothing stored after session ends.</div>
      <div class="nb ok">Designed for early support screening — not final clinical diagnosis.</div>
    </div>
    <div class="card">
      <p class="card-title">Support helplines</p>
      <div class="nb ok"><b>iCall:</b> 9152987821 · Mon–Sat 8am–10pm</div>
      <div class="nb ok"><b>Vandrevala Foundation:</b> 1860-2662-345 · 24/7</div>
      <div class="nb ok"><b>NIMHANS:</b> 080-46110007 · National</div>
    </div>
    <div class="card">
      <p class="card-title">🌱 Today's wellness tip</p>
      <div class="quote">{get_tip()}</div>
      <p style="font-size:13px;color:var(--muted)">Small consistent actions build emotional resilience over time.</p>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<p class="card-title">Start screening</p>', unsafe_allow_html=True)

    mode = st.radio("Input type", ["📝 Text", "🎙 Audio"], horizontal=True)
    st.markdown("<br>", unsafe_allow_html=True)

    SAMPLES = {
        "Choose sample →": "",
        "Low risk — peaceful day":
            "Had a peaceful day. I completed my work and felt grateful after talking to my friends. Things feel manageable.",
        "Medium risk — overwhelmed":
            "I feel overwhelmed and tired lately. Everything feels too much and I cannot focus properly no matter how hard I try.",
        "High risk — hopeless":
            "I feel hopeless. Nothing is getting better and everyone would be better off without me. I don't see the point anymore.",
    }

    text_input = ""
    audio_file = None
    run = False

    if "Text" in mode:
        # Sample selectbox with light background
        st.markdown('<p style="font-size:13.5px;font-weight:600;color:var(--text);margin-bottom:5px">Try a sample</p>',
                    unsafe_allow_html=True)
        sample_choice = st.selectbox(
            "sample", list(SAMPLES.keys()),
            index=list(SAMPLES.keys()).index(st.session_state.selected_sample)
                  if st.session_state.selected_sample in SAMPLES else 0,
            label_visibility="collapsed",
        )
        if sample_choice != st.session_state.selected_sample:
            st.session_state.selected_sample = sample_choice

        st.markdown('<p style="font-size:13.5px;font-weight:600;color:var(--text);margin:12px 0 5px">Message or transcript</p>',
                    unsafe_allow_html=True)
        text_input = st.text_area(
            "msg", value=SAMPLES[sample_choice], height=150,
            placeholder="Paste a message, journal entry, or chat transcript here…",
            label_visibility="collapsed",
        )
        explain = st.checkbox("Show word-level explanation (SHAP)", value=True)
        run = st.button("Analyse text →", use_container_width=True)
    else:
        st.markdown('<div class="nb warn">Supported: WAV, MP3, OGG, FLAC, M4A · Max 25 MB</div>',
                    unsafe_allow_html=True)
        audio_file = st.file_uploader("Upload audio", type=["wav","mp3","ogg","flac","m4a"],
                                      label_visibility="collapsed")
        run = st.button("Analyse audio →", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ── INFERENCE ─────────────────────────────────────────────────────────────────
if run:
    with st.spinner("Analysing…"):
        try:
            if "Text" in mode:
                if not text_input.strip(): st.warning("Please enter text first."); st.stop()
                resp = requests.post(f"{API_BASE}/text/analyse",
                                     json={"text": text_input, "explain": explain,
                                           "mood": st.session_state.mood}, timeout=120)
            else:
                if audio_file is None: st.warning("Please upload a file first."); st.stop()
                resp = requests.post(f"{API_BASE}/audio/analyse",
                                     files={"file":(audio_file.name, audio_file,
                                                    audio_file.type or "audio/wav")}, timeout=120)
            if resp.status_code != 200: st.error(f"API error {resp.status_code}"); st.stop()
            st.session_state.last_result = resp.json()
        except requests.exceptions.ConnectionError:
            # Use sample-based result if a sample is selected, else text-based
            if "Text" in mode and st.session_state.selected_sample in SAMPLE_RESULTS and \
               SAMPLE_RESULTS[st.session_state.selected_sample] is not None:
                st.session_state.last_result = SAMPLE_RESULTS[st.session_state.selected_sample]
            else:
                st.session_state.last_result = demo_result_from_text(
                    text_input if "Text" in mode else "")
            st.info("API offline — showing demo result.")
        except Exception as e:
            st.error(f"Error: {e}"); st.stop()

# ── RESULTS ───────────────────────────────────────────────────────────────────
if st.session_state.last_result:
    data  = st.session_state.last_result
    score = data.get("risk_score", 0)
    level = data.get("risk_level", "UNKNOWN")
    color = data.get("risk_color", "#6b4423")
    flags = data.get("flags", [])
    tokens= data.get("top_tokens", [])

    st.markdown('<div class="div"></div>', unsafe_allow_html=True)
    st.markdown("## Screening result")

    r1, r2 = st.columns([1, 1], gap="large")

    with r1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">Risk score</p>', unsafe_allow_html=True)
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            number={"suffix":" / 100","font":{"color":color,"size":36,"family":"Playfair Display"}},
            gauge={"axis":{"range":[0,100],"tickfont":{"color":"#7A5C42","size":9}},
                   "bar":{"color":color,"thickness":0.26},"bgcolor":"#FEFCF8","bordercolor":"#DDD0BB",
                   "steps":[{"range":[0,30],"color":"#EDF7EE"},{"range":[30,60],"color":"#FEF8E6"},
                             {"range":[60,80],"color":"#FEF0E4"},{"range":[80,100],"color":"#FDF0F0"}],
                   "threshold":{"line":{"color":color,"width":3},"thickness":0.85,"value":score}},
            title={"text":f"<b>{level}</b>","font":{"color":color,"size":15,"family":"DM Sans"}},
        ))
        fig.update_layout(height=268,paper_bgcolor="#FEFCF8",font={"color":"#271506"},
                          margin=dict(t=28,b=6,l=8,r=8))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f'<div class="nb warn" style="font-size:12.5px">{data.get("disclaimer","")}</div>',
                    unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with r2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">Flags & recommended action</p>', unsafe_allow_html=True)
        if flags:
            for flag in flags:
                cls = "high" if any(x in flag for x in ["IMMEDIATE","CLINICAL"]) else "med"
                dot = "#B83232" if cls=="high" else "#C89A20"
                st.markdown(f'<div class="flag {cls}"><div class="fdot" style="background:{dot}"></div>'
                            f'<span>{flag.replace("_"," ").title()}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="flag low"><div class="fdot" style="background:#3A8A50"></div>'
                        '<span>No immediate flags — continue standard monitoring</span></div>',
                        unsafe_allow_html=True)

        st.markdown('<br><p style="font-size:14px;font-weight:600;color:var(--br3);margin-bottom:10px">Score breakdown</p>',
                    unsafe_allow_html=True)
        ts  = data.get("text_score", score)
        aus = data.get("audio_score")
        ws  = wellness_score(score)
        for lbl, val, col in [("Text signal", ts, "#9C6B3C"),
                               *([("Audio signal", aus, "#4A7C50")] if aus else []),
                               ("Wellness estimate", ws, "#2A5C38")]:
            st.markdown(f"""<div class="pbar-wrap">
              <div class="pbar-row"><span>{lbl}</span>
                <span style="font-family:'DM Mono',monospace;font-weight:600;color:{col}">{val:.0f}/100</span></div>
              <div class="pbar-track"><div class="pbar-fill" style="width:{val}%;background:{col}"></div></div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if tokens:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">Word-level explanation (SHAP)</p>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:13.5px;color:var(--muted);margin-bottom:12px">'
                    'Words that most influenced the prediction. '
                    '<span style="color:#8B1A1A;font-weight:700">Red</span> = increases risk &nbsp;·&nbsp; '
                    '<span style="color:#2A5C38;font-weight:700">Green</span> = reduces risk</p>',
                    unsafe_allow_html=True)
        chips = "".join(
            f'<span class="tok {"r" if t.get("direction")=="risk-increasing" else "s"}">'
            f'{t.get("token","")} <span class="tval">{t.get("shap_value",0):+.3f}</span></span>'
            for t in tokens)
        st.markdown(f'<div class="tgrid">{chips}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Challenge + plan
    if score >= 80:
        ct="Immediate care mode"
        cp="Do not stay alone with this result. Contact a trusted person now and call emergency support if there is any immediate risk."
        p1,p2,p3="Call or message someone you trust right now.","Keep distance from anything that can harm you.","Share the result with a counsellor or doctor."
    elif score >= 60:
        ct="High support mode"
        cp="This result needs attention. Slow down, ground yourself, and plan a real conversation with someone safe."
        p1,p2,p3="Book a counselling conversation.","Write what triggered this feeling today.","Do one grounding exercise for 3 minutes."
    elif score >= 30:
        ct="Reset and monitor mode"
        cp="Your result shows stress signals. Track your mood and reduce overload today. Do not ignore it, but do not panic either."
        p1,p2,p3="Take a 10-minute no-phone break.","Write 3 things that are stressing you.","Drink water and take a short walk."
    else:
        ct="Wellness boost mode"
        cp="Your result looks low-risk right now. Keep the healthy pattern going and build a small emotional check-in habit."
        p1,p2,p3="Save one thing that went well today.","Send a message to someone you appreciate.","Plan sleep and screen cut-off time."

    st.markdown(f"""
    <div class="cbox"><h3>{ct}</h3><p>{cp}</p></div>
    <div class="card">
      <p class="card-title">What you can try after this test</p>
      <div class="plan-grid">
        <div class="plan"><b>1. Grounding</b>
          <p>Try 5-4-3-2-1: notice 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.</p></div>
        <div class="plan"><b>2. Box breathing</b>
          <p>Inhale 4s → hold 4s → exhale 4s → hold 4s. Repeat 4 rounds before anything else.</p></div>
        <div class="plan"><b>3. Journal prompt</b>
          <p>Write: "Right now I feel ___ because ___. The smallest next step I can take is ___."</p></div>
      </div>
      <div class="quote">{p1} &nbsp;·&nbsp; {p2} &nbsp;·&nbsp; {p3}</div>
      <div class="todo-grid">
        <div class="todo">✅ Retake screening after 24 hours if feelings continue.</div>
        <div class="todo">✅ Screenshot your result for a counsellor session.</div>
        <div class="todo">✅ Avoid big decisions while emotionally overwhelmed.</div>
        <div class="todo">✅ Reach out early — don't wait for things to worsen.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Try now section header ────────────────────────────────────────────────
    st.markdown("""
    <div style="margin:32px 0 20px">
      <h2 style="font-family:'Playfair Display',serif;font-size:28px;color:#6B4220;
          border-bottom:2px solid #E4D3BC;padding-bottom:12px;margin:0">
        Try now
      </h2>
    </div>
    """, unsafe_allow_html=True)

    # ── Row 1: Chart + Breathing (side by side) ───────────────────────────────
    row1_l, row1_r = st.columns([1, 1], gap="large")

    with row1_l:
        st.markdown('<div class="card" style="height:100%">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📊 Emotional breakdown</p>', unsafe_allow_html=True)
        emotions = emotion_breakdown(score)
        fig2 = go.Figure(data=[go.Bar(
            x=list(emotions.keys()), y=list(emotions.values()),
            marker_color=["#C08060","#D4A070","#B07050","#5A9A65"],
            marker_line_width=0,
        )])
        fig2.update_layout(
            height=200, margin=dict(l=8,r=8,t=10,b=8),
            paper_bgcolor="#FEFCF8", plot_bgcolor="#FEFCF8",
            yaxis=dict(range=[0,100], gridcolor="#EAD9C2", title=""),
            xaxis=dict(title=""), font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown(f"""
        <div class="metric-grid">
          <div class="metric"><b>{ws}</b><p>Wellness</p></div>
          <div class="metric"><b>{st.session_state.mood_emoji}</b><p>{st.session_state.mood}</p></div>
          <div class="metric"><b>{len(tokens)}</b><p>Key words</p></div>
          <div class="metric"><b>{len(flags)}</b><p>Flags</p></div>
        </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with row1_r:
        st.markdown('<div class="card" style="height:100%">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🫁 60-second calm tool</p>', unsafe_allow_html=True)
        st.markdown('<div class="breath-orb">🫁</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0">
          <div class="todo">① Inhale slowly for <b>4 seconds</b></div>
          <div class="todo">② Hold breath for <b>4 seconds</b></div>
          <div class="todo">③ Exhale gently for <b>6 seconds</b></div>
          <div class="todo">④ Repeat <b>5 times</b> before anything else</div>
        </div>""", unsafe_allow_html=True)
        if st.button("✅  I completed this breathing exercise", use_container_width=True, key="breath_btn"):
            st.session_state.breath_done = True
        if st.session_state.breath_done:
            st.markdown('<div class="nb ok" style="margin-top:10px">Good. Now take one small next step — not a big life decision.</div>',
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 2: Journal + Music (side by side) ────────────────────────────────
    row2_l, row2_r = st.columns([1, 1], gap="large")

    with row2_l:
        st.markdown('<div class="card" style="height:100%">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">📖 Session journal</p>', unsafe_allow_html=True)
        st.markdown("""
        <div class="journal-prompt">
          <b>Prompt:</b> Right now I feel ___ because ___. The smallest safe next step I can take is ___.
        </div>""", unsafe_allow_html=True)
        j_text = st.text_area(
            "journal", height=110,
            placeholder="Write 2–3 honest lines. Stays only in this session.",
            label_visibility="collapsed",
        )
        jc1, jc2 = st.columns([3, 1])
        with jc1:
            if st.button("Save entry →", use_container_width=True, key="save_journal"):
                if j_text.strip():
                    st.session_state.journal_entries.append({
                        "time": datetime.now().strftime("%H:%M"),
                        "text": j_text.strip(),
                    })
                    st.success("Saved.")
                else:
                    st.warning("Write something first.")
        with jc2:
            st.markdown(
                f'<div style="text-align:center;padding-top:10px;font-size:13px;'
                f'color:var(--muted)"><b>{len(st.session_state.journal_entries)}</b><br>entries</div>',
                unsafe_allow_html=True,
            )
        for entry in st.session_state.journal_entries[-3:]:
            st.markdown(
                f'<div class="j-entry"><div class="j-time">{entry["time"]}</div>{entry["text"]}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with row2_r:
        st.markdown('<div class="card" style="height:100%">', unsafe_allow_html=True)
        st.markdown('<p class="card-title">🎵 Relaxation resources</p>', unsafe_allow_html=True)
        st.markdown("""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:4px">
          <div class="mcard">
            <a href="https://www.youtube.com/results?search_query=5+minute+breathing+exercise" target="_blank">🫁 Breathing</a>
            <p>Quick calming exercise</p>
          </div>
          <div class="mcard">
            <a href="https://www.youtube.com/results?search_query=calm+rain+sounds+for+anxiety" target="_blank">🌧 Rain Sounds</a>
            <p>Soft background audio</p>
          </div>
          <div class="mcard">
            <a href="https://www.youtube.com/results?search_query=guided+meditation+for+stress+10+minutes" target="_blank">🧘 Meditation</a>
            <p>10-minute reset</p>
          </div>
          <div class="mcard">
            <a href="https://www.youtube.com/results?search_query=study+calm+lofi+music" target="_blank">🎧 Calm Music</a>
            <p>Focus without overload</p>
          </div>
        </div>

        <div style="margin-top:20px">
          <p class="card-title" style="font-size:16px!important;margin-bottom:10px">📞 Quick helplines</p>
          <div class="nb ok"><b>iCall:</b> 9152987821 · Mon–Sat 8am–10pm</div>
          <div class="nb ok"><b>Vandrevala Foundation:</b> 1860-2662-345 · 24/7</div>
          <div class="nb ok"><b>NIMHANS:</b> 080-46110007 · National</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ── RESOURCES & FOOTER ────────────────────────────────────────────────────────
st.markdown("""
<div class="res-grid">
  <div class="res"><h4>🗣 Talk to someone</h4>
    <p>Share your result with a counsellor, mentor, or trusted adult. You don't have to carry this alone.</p></div>
  <div class="res"><h4>📖 Understand the result</h4>
    <p>The score shows possible risk signals, not a final medical diagnosis. A professional can help interpret it.</p></div>
  <div class="res"><h4>🚨 Emergency help</h4>
    <p>If someone is in immediate danger, call <b>112</b> (India) or your local emergency number without delay.</p></div>
</div>
<div class="footer">
  MindBridge &nbsp;·&nbsp; Mental Health Screening &nbsp;·&nbsp; RoBERTa + SHAP &nbsp;·&nbsp;
  Not a clinical diagnostic instrument &nbsp;·&nbsp; No personal data stored &nbsp;·&nbsp;
  Built by Priya Singh
</div>
""", unsafe_allow_html=True)

# Close page wrapper
st.markdown("</div>", unsafe_allow_html=True)
