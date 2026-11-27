"""Shared theme, components and API client for the MindBridge dashboard."""

import html as _html
import os
import re

import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")

MOODS = {
    "thriving": {"bg": "#DDF7EC", "fg": "#0F6B4A", "bar": "#7FD9B0"},
    "okay-ish": {"bg": "#E3EFFF", "fg": "#1D5FA8", "bar": "#9CC2F0"},
    "meh":      {"bg": "#FFF6CC", "fg": "#6B4F00", "bar": "#E8C64A"},
    "stressed": {"bg": "#FFE6DA", "fg": "#8F3A12", "bar": "#F4A57F"},
    "low":      {"bg": "#EFEAFF", "fg": "#4A2FC9", "bar": "#B9A8FF"},
}

LEVELS = {
    "LOW":      {"bg": "#DDF7EC", "fg": "#0B4F37", "ring": "#1E9E6A", "label": "LOW · you seem okay"},
    "MEDIUM":   {"bg": "#FFF6CC", "fg": "#5A3E00", "ring": "#E8A93A", "label": "MEDIUM · keep an eye on it"},
    "HIGH":     {"bg": "#FFE6DA", "fg": "#6B2507", "ring": "#E07040", "label": "HIGH · worth talking to someone"},
    "CRITICAL": {"bg": "#FFE0E0", "fg": "#7A1414", "ring": "#C53030", "label": "please reach out to someone now"},
}

HELPLINES = [
    {"name": "Tele-MANAS (Govt. of India)", "contact": "14416", "tel": "14416", "hours": "24x7 · free · your language"},
    {"name": "iCall (TISS)", "contact": "9152987821", "tel": "9152987821", "hours": "Mon–Sat · 8am–10pm"},
    {"name": "Emergency", "contact": "112", "tel": "112", "hours": "if you're in danger right now"},
]

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, p, label, input, textarea, button { font-family: 'Inter', system-ui, sans-serif; }
h1, h2, h3, .mb-display { font-family: 'Bricolage Grotesque', sans-serif !important; letter-spacing: -0.03em; color: #1E1B2E; }
#MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; }
.block-container { padding-top: 2rem; max-width: 1200px; }
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1.5px solid #ECE8F7; }
.stButton > button, .stDownloadButton > button, .stLinkButton > a, .stFormSubmitButton > button {
  border-radius: 999px !important; font-weight: 600 !important; padding: 0.55rem 1.3rem !important; min-height: 44px; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background: #6D4AFF; border-color: #6D4AFF; }
.stTextArea textarea, .stTextInput input { border-radius: 18px !important; background: #FCFBFF !important; }
[data-testid="stAudioInput"], [data-testid="stFileUploaderDropzone"] { border-radius: 18px; }
div[data-testid="stExpander"] details { border-radius: 18px; border-color: #ECE8F7; }
.mb-card { border-radius: 26px; padding: 22px 24px; margin-bottom: 14px; border: 1.5px solid transparent; }
.mb-white { background: #FFFFFF; border-color: #ECE8F7; }
.mb-lav { background: #EFEAFF; color: #2E1A8F; } .mb-mint { background: #DDF7EC; color: #0B4F37; }
.mb-peach { background: #FFE6DA; color: #3D1A08; } .mb-butter { background: #FFF6CC; color: #3D2A00; }
.mb-sky { background: #E3EFFF; color: #12325A; } .mb-alert { background: #FDF0F0; border: 2px solid #C53030; color: #3D0A0A; }
.mb-card h3 { margin: 0 0 6px 0; font-size: 1.3rem; color: inherit; }
.mb-card p { margin: 0; line-height: 1.5; }
.mb-chip { display: inline-block; padding: 6px 12px; border-radius: 999px; font-size: 0.85rem; font-weight: 600; margin: 3px 6px 3px 0; }
.mb-kicker { font-size: 0.85rem; font-weight: 600; color: #5B5670; }
.mb-big { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 2.6rem; line-height: 1.05; }
.mb-mark-up { background: #FFC4AA; color: #6B2507; border-radius: 8px; padding: 1px 6px; }
.mb-mark-down { background: #C9F2DF; color: #0B4F37; border-radius: 8px; padding: 1px 6px; }
.mb-bar { height: 10px; border-radius: 999px; background: #E4DDFF; overflow: hidden; }
.mb-bar > div { height: 10px; border-radius: 999px; }
.mb-tel { display: inline-block; margin-top: 10px; padding: 10px 18px; border-radius: 999px; background: #B24A1C; color: #FFFFFF !important; text-decoration: none; font-weight: 600; }
.mb-tel.soft { background: #FFF1EA; color: #8F3A12 !important; }
</style>
"""


def html(markup: str):
    """Render HTML. Lines are stripped so Markdown never turns indented HTML into code."""
    st.markdown("\n".join(line.strip() for line in markup.splitlines() if line.strip()), unsafe_allow_html=True)


def esc(text) -> str:
    return _html.escape(str(text if text is not None else ""))


def card(title: str, body: str, tone: str = "white", kicker: str | None = None):
    k = f'<div class="mb-kicker" style="color:inherit;opacity:.85">{esc(kicker)}</div>' if kicker else ""
    html(f'<div class="mb-card mb-{tone}">{k}<h3>{esc(title)}</h3><p>{body}</p></div>')


def chip(text: str, bg: str, fg: str) -> str:
    return f'<span class="mb-chip" style="background:{bg};color:{fg}">{esc(text)}</span>'


def page_header(title: str, kicker: str = "", subtitle: str = ""):
    k = f'<div class="mb-kicker">{esc(kicker)}</div>' if kicker else ""
    s = f'<p style="color:#5B5670;font-size:1.05rem;margin:4px 0 0 0">{esc(subtitle)}</p>' if subtitle else ""
    html(f'<div style="margin-bottom:18px">{k}<h1 style="font-size:2.7rem;margin:4px 0 0 0;line-height:1.05">{esc(title)}</h1>{s}</div>')


def stress_ring(score: float, level: str, caption: str = "stress meter") -> str:
    lv = LEVELS.get(level, LEVELS["MEDIUM"])
    circ = 2 * 3.14159 * 80
    dash = max(0.0, min(100.0, score)) / 100 * circ
    return f"""
    <div class="mb-card" style="background:{lv['bg']};color:{lv['fg']};text-align:center">
    <div style="position:relative;width:190px;height:190px;margin:0 auto">
    <svg width="190" height="190" viewBox="0 0 200 200" role="img" aria-label="Stress {score:.0f} out of 100">
    <circle cx="100" cy="100" r="80" fill="none" stroke="#FFFFFF" stroke-width="20"></circle>
    <circle cx="100" cy="100" r="80" fill="none" stroke="{lv['ring']}" stroke-width="20" stroke-linecap="round"
    stroke-dasharray="{dash:.0f} {circ:.0f}" transform="rotate(-90 100 100)"></circle></svg>
    <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">
    <span class="mb-big" style="font-size:3.2rem">{score:.0f}</span>
    <span style="font-size:.8rem;font-weight:600">{esc(caption)}</span></div></div>
    <div style="margin-top:12px"><span class="mb-chip" style="background:#FFFFFF;color:{lv['fg']}">{esc(lv['label'])}</span></div>
    </div>"""


def clean_token(tok: str) -> str:
    return re.sub(r"^(Ġ|▁|##)", "", str(tok)).strip()


def highlight(text: str, tokens: list[dict]) -> str:
    """Wrap words that pushed stress up (peach) or down (mint)."""
    out = esc(text)
    seen = set()
    for t in sorted(tokens or [], key=lambda t: -len(clean_token(t.get("token", "")))):
        word = clean_token(t.get("token", ""))
        if len(word) < 3 or word.lower() in seen:
            continue
        seen.add(word.lower())
        cls = "mb-mark-up" if t.get("direction") == "risk-increasing" else "mb-mark-down"
        out = re.sub(rf"(?i)(?<![\w>])({re.escape(esc(word))})(?![\w<])", rf'<mark class="{cls}">\1</mark>', out, count=1)
    return out


def crisis_banner(resources=None, contact=None):
    rows = "".join(
        f'<div style="margin:6px 0"><b>{esc(r["name"])}:</b> '
        f'<a href="tel:{esc(r.get("tel", r["contact"]))}" style="font-weight:700;color:#7A1414">{esc(r["contact"])}</a>'
        f' <span style="opacity:.8">· {esc(r.get("hours", ""))}</span></div>'
        for r in (resources or HELPLINES))
    contact_html = ""
    if contact and contact.get("phone"):
        phone = re.sub(r"[^\d]", "", contact["phone"])
        msg = requests.utils.quote("hey, i'm not doing okay right now. can you call me or come over?")
        contact_html = (f'<a class="mb-tel" href="https://wa.me/{phone}?text={msg}" target="_blank">'
                        f'message {esc(contact.get("name") or "your trusted person")} on whatsapp</a>')
    html(f"""<div class="mb-card mb-alert" role="alert">
    <div class="mb-display" style="font-size:1.4rem;font-weight:800;margin-bottom:6px">you don't have to go through this alone</div>
    <p style="margin-bottom:8px">what you shared sounds really heavy. please talk to someone right now — these are free and confidential:</p>
    {rows}{contact_html}
    <p style="margin-top:10px;font-size:.9rem">in immediate danger? call <b>112</b> or go to the nearest hospital.</p></div>""")


# ── API client ────────────────────────────────────────────────────────────────

class ApiError(Exception):
    pass


def api(method: str, path: str, raw: bool = False, **kwargs):
    headers = kwargs.pop("headers", {})
    token = st.session_state.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.request(method, f"{API_BASE}{path}", headers=headers, timeout=180, **kwargs)
    except requests.exceptions.ConnectionError:
        raise ApiError("the mindbridge server is offline right now. please try again in a bit.")
    except requests.exceptions.Timeout:
        raise ApiError("that took too long. please try again.")
    if resp.status_code == 401 and token:
        logout()
        st.rerun()
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
            if isinstance(detail, list):  # pydantic validation errors
                detail = "; ".join(d.get("msg", str(d)) for d in detail)
        except Exception:
            detail = resp.text
        raise ApiError(str(detail))
    return resp.content if raw else resp.json()


def safe_api(*args, **kwargs):
    """Like api() but shows a friendly error and returns None."""
    try:
        return api(*args, **kwargs)
    except ApiError as e:
        st.error(str(e))
        return None


def current_user() -> dict:
    return st.session_state.get("user") or {}


def logout():
    for k in ("token", "user", "last_result"):
        st.session_state.pop(k, None)
