# ─────────────────────────────────────────────────────────────
# app.py — MindBridge Lite  |  Streamlit Dashboard
# Run: streamlit run app.py
# ─────────────────────────────────────────────────────────────

import streamlit as st
import plotly.graph_objects as go
import time
from predict import predict, explain

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="MindBridge — Mental Health Risk Detector",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .main { background: #0F172A; }

    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 100%);
    }

    /* Header */
    .mb-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    .mb-title {
        font-size: 2.8rem;
        font-weight: 600;
        color: #F8FAFC;
        letter-spacing: -0.5px;
        margin: 0;
    }
    .mb-title span { color: #818CF8; }
    .mb-sub {
        font-size: 1rem;
        color: #64748B;
        margin-top: 0.4rem;
    }

    /* Cards */
    .mb-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Risk badge */
    .risk-badge {
        display: inline-block;
        padding: 0.3rem 1rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.9rem;
        letter-spacing: 0.5px;
    }

    /* SHAP token chips */
    .token-chip {
        display: inline-block;
        padding: 0.3rem 0.7rem;
        border-radius: 6px;
        font-family: 'DM Mono', monospace;
        font-size: 0.82rem;
        margin: 0.25rem;
        font-weight: 500;
    }

    /* Disclaimer */
    .disclaimer {
        background: #1E293B;
        border-left: 3px solid #F59E0B;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.8rem;
        color: #94A3B8;
        margin-top: 1rem;
    }

    /* Prob bars */
    .prob-row {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin: 0.4rem 0;
        font-size: 0.85rem;
        color: #CBD5E1;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stTextArea textarea {
        background: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #F1F5F9 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.95rem !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 0.6rem 2rem !important;
        width: 100% !important;
        transition: opacity 0.2s !important;
    }
    .stButton > button:hover { opacity: 0.85 !important; }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div class="mb-header">
    <p class="mb-title">Mind<span>Bridge</span></p>
    <p class="mb-sub">Early mental health signal detector &nbsp;·&nbsp; NLP + Explainable AI &nbsp;·&nbsp; For counsellors & researchers</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Layout ────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

# ── Left: Input ───────────────────────────────────────────────
with col_left:
    st.markdown("#### 📝 Input Text")
    st.caption("Paste a message, journal entry, or social media post")

    sample_texts = {
        "Select a sample...": "",
        "😊 Positive (Low risk)":
            "Had such a good day today! Finally finished my project and went out with friends. Feeling really grateful.",
        "😔 Mild signal":
            "I've been feeling really overwhelmed lately. Everything feels like too much and I can't seem to catch up no matter what I do. I'm exhausted all the time.",
        "🚨 High risk signal":
            "I don't see the point anymore. Nothing gets better no matter how hard I try. I've been thinking that everyone would be better off without me around.",
    }

    chosen = st.selectbox("Try a sample:", list(sample_texts.keys()))
    prefill = sample_texts[chosen]

    user_text = st.text_area(
        "Or type your own:",
        value=prefill,
        height=180,
        placeholder="Enter text to analyse...",
        label_visibility="collapsed" if prefill else "visible",
    )

    explain_toggle = st.checkbox(
        "Show word-level explanations (SHAP)",
        value=True,
        help="Highlights which words most influenced the prediction"
    )

    analyse_btn = st.button("Analyse →", type="primary")


# ── Right: Results ────────────────────────────────────────────
with col_right:
    st.markdown("#### 📊 Risk Assessment")

    if not analyse_btn:
        st.markdown("""
        <div class="mb-card" style="text-align:center; padding: 3rem 1rem; color: #475569;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem">🧠</div>
            <div style="font-size: 0.95rem">Enter text and click Analyse to see results</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        if not user_text.strip():
            st.warning("Please enter some text first.")
        else:
            with st.spinner("Analysing..."):
                result = predict(user_text.strip())

            score = result["risk_score"]
            color = result["risk_color"]
            level = result["risk_level"]
            emoji = result["risk_emoji"]
            probs = result["probs"]

            # ── Gauge ──────────────────────────────────────────
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                number={"suffix": "/100", "font": {"color": color, "size": 36}},
                gauge={
                    "axis": {"range": [0, 100],
                             "tickcolor": "#475569",
                             "tickfont": {"color": "#64748B", "size": 10}},
                    "bar":  {"color": color, "thickness": 0.3},
                    "bgcolor": "#1E293B",
                    "bordercolor": "#334155",
                    "steps": [
                        {"range": [0,  40], "color": "#14532D22"},
                        {"range": [40, 70], "color": "#78350F22"},
                        {"range": [70,100], "color": "#7F1D1D22"},
                    ],
                    "threshold": {
                        "line": {"color": color, "width": 3},
                        "thickness": 0.8,
                        "value": score,
                    },
                },
            ))
            fig.update_layout(
                height=240,
                margin=dict(t=20, b=10, l=20, r=20),
                paper_bgcolor="rgba(0,0,0,0)",
                font={"color": "#CBD5E1"},
            )
            st.plotly_chart(fig, use_container_width=True)

            # ── Risk level badge ───────────────────────────────
            st.markdown(f"""
            <div style="text-align:center; margin: -0.5rem 0 1rem 0">
                <span class="risk-badge" style="background:{color}22; color:{color}; border: 1px solid {color}44">
                    {emoji} &nbsp; {level.upper()}
                </span>
            </div>
            """, unsafe_allow_html=True)

            # ── Probability breakdown ──────────────────────────
            st.markdown("**Confidence breakdown:**")
            bar_data = [
                ("No Signal",  probs["no_signal"], "#22C55E"),
                ("Mild Risk",  probs["mild_risk"], "#F59E0B"),
                ("High Risk",  probs["high_risk"], "#EF4444"),
            ]
            for label, pct, bar_color in bar_data:
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"""
                    <div style="background:#1E293B; border-radius:4px; height:10px; margin:4px 0; overflow:hidden">
                        <div style="width:{pct}%; background:{bar_color}; height:100%; border-radius:4px;
                                    transition: width 0.5s ease"></div>
                    </div>
                    <div style="font-size:0.78rem; color:#64748B; margin-bottom:6px">{label}</div>
                    """, unsafe_allow_html=True)
                with col_b:
                    st.markdown(f"""
                    <div style="color:{bar_color}; font-weight:600;
                                font-size:0.9rem; text-align:right; padding-top:2px">
                        {pct}%
                    </div>
                    """, unsafe_allow_html=True)

            # ── Flags ──────────────────────────────────────────
            if score >= 70:
                st.error("🚨 Immediate counsellor review recommended")
            elif score >= 40:
                st.warning("⚠ Monitoring and follow-up advised")
            else:
                st.success("✅ No immediate flags detected")

            # ── Disclaimer ─────────────────────────────────────
            st.markdown(f"""
            <div class="disclaimer">{result['disclaimer']}</div>
            """, unsafe_allow_html=True)


# ── SHAP Explanations (full width below) ─────────────────────
if analyse_btn and user_text.strip() and explain_toggle:
    st.markdown("---")
    st.markdown("#### 🔍 Word-Level Explanations")
    st.caption("Which words most influenced the prediction — red = increases risk, green = reduces risk")

    with st.spinner("Computing SHAP explanations (takes ~10–15 seconds)..."):
        try:
            tokens = explain(user_text.strip())

            chips_html = ""
            for tok in tokens:
                chips_html += f"""
                <span class="token-chip"
                      style="background:{tok['color']}33; color:{tok['color']};
                             border: 1px solid {tok['color']}66"
                      title="{tok['direction']} ({tok['value']:+.4f})">
                    {tok['token']}
                    <span style="opacity:0.7; font-size:0.75em"> {tok['value']:+.3f}</span>
                </span>"""

            st.markdown(f"""
            <div class="mb-card">
                {chips_html}
                <div style="margin-top:1rem; font-size:0.78rem; color:#475569">
                    Values show SHAP contribution toward high-risk class.
                    Positive = pushes toward risk. Negative = pushes away from risk.
                </div>
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.info(f"SHAP unavailable in this environment: {e}")


# ── Footer ────────────────────────────────────────────────────
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div style="font-size:0.8rem; color:#475569">
        <b style="color:#64748B">Model</b><br>
        RoBERTa-base fine-tuned<br>
        on mental health corpus
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div style="font-size:0.8rem; color:#475569; text-align:center">
        <b style="color:#64748B">Explainability</b><br>
        SHAP token attribution<br>
        (target: high-risk class)
    </div>""", unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div style="font-size:0.8rem; color:#475569; text-align:right">
        <b style="color:#64748B">Privacy</b><br>
        No data stored<br>
        Stateless inference
    </div>""", unsafe_allow_html=True)
