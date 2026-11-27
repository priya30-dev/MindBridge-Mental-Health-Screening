"""End-to-end API tests for accounts, check-ins, journal, questionnaires,
reports and privacy. ML models are replaced by small fakes so these run in
CI without the trained weights."""

import io
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

STUBBED = ["src.text_model", "src.audio_model", "src.explainer", "src.utils", "src.risk_model", "src.model_loader"]
APP_MODULES_PREFIX = ("api",)


def _fake_predict_text(text, tok, model):
    t = text.lower()
    if any(w in t for w in ("sad", "tired", "overwhelmed", "exams")):
        return {"label": 0, "emotion": "sadness", "confidence": 80.0, "probabilities": []}
    return {"label": 1, "emotion": "joy", "confidence": 90.0, "probabilities": []}


def _fake_predict_risk(text, tok, model):
    t = text.lower()
    if any(w in t for w in ("sad", "tired", "overwhelmed", "exams")):
        return {"label": 1, "label_name": "Mild Risk", "risk_score": 68.0,
                "probabilities": {"No Signal": 0.1, "Mild Risk": 0.44, "High Risk": 0.46}}
    return {"label": 0, "label_name": "No Signal", "risk_score": 5.0,
            "probabilities": {"No Signal": 0.9, "Mild Risk": 0.1, "High Risk": 0.0}}


FAKE_MODELS = {"risk_tokenizer": "t", "risk_model": "m", "audio_model": "a", "audio_scaler": "s"}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    mp = pytest.MonkeyPatch()
    mp.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    mp.setenv("COUNSELLOR_EMAILS", "counsellor@college.edu")
    mp.setenv("AUTH_RATE_LIMIT", "1000")

    tm = types.ModuleType("src.text_model")
    tm.load_text_model = lambda *a, **k: ("tok", "model")
    tm.predict_text = _fake_predict_text
    am = types.ModuleType("src.audio_model")
    am.load_audio_model = lambda *a, **k: ("am", "scaler")
    am.predict_audio_features = lambda f, m, s: {"label": 0, "probabilities": [0.6, 0.4], "risk_score": 40.0}
    ex = types.ModuleType("src.explainer")
    ex.explain_text = lambda **k: {"top_tokens": [
        {"token": "exams", "shap_value": 0.4, "direction": "risk-increasing"},
        {"token": "friends", "shap_value": -0.2, "direction": "risk-reducing"}]}
    ut = types.ModuleType("src.utils")
    ut.extract_audio_features = lambda path: np.zeros(122)
    rm = types.ModuleType("src.risk_model")
    rm.predict_risk = _fake_predict_risk
    rm.explain_risk = lambda text, tok, model, top_k=5: {"top_tokens": [
        {"token": "exams", "shap_value": 0.4, "direction": "risk-increasing"},
        {"token": "friends", "shap_value": -0.2, "direction": "risk-reducing"}]}
    ml = types.ModuleType("src.model_loader")
    ml.load_available_models = lambda: dict(FAKE_MODELS)

    saved = {k: v for k, v in sys.modules.items() if k in STUBBED or k.startswith(APP_MODULES_PREFIX)}
    for k in list(saved):
        sys.modules.pop(k, None)
    for name, mod in zip(STUBBED, (tm, am, ex, ut, rm, ml)):
        sys.modules[name] = mod

    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as c:
        yield c

    for k in [k for k in sys.modules if k in STUBBED or k.startswith(APP_MODULES_PREFIX)]:
        sys.modules.pop(k, None)
    sys.modules.update(saved)
    mp.undo()


def _register(client, email, password="supersecret1"):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Priya"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _wav_bytes(seconds=1.5, sr=16000):
    import soundfile as sf
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    y = (0.3 * np.sin(2 * np.pi * 180 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV")
    return buf.getvalue()


def test_register_login_and_me(client):
    _register(client, "a@example.com")
    assert client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "supersecret1"}).status_code == 409
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrongpass1"}).status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "supersecret1"})
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["email"] == "a@example.com" and me["role"] == "user"


def test_login_rate_limit(client):
    from api.routers import auth
    auth._ATTEMPTS.clear()
    old = auth._MAX
    auth._MAX = 3
    try:
        codes = [client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "nopenope1"}).status_code
                 for _ in range(4)]
        assert codes == [401, 401, 401, 429]
    finally:
        auth._MAX = old
        auth._ATTEMPTS.clear()


def test_endpoints_require_login(client):
    assert client.get("/api/v1/checkins").status_code == 401
    assert client.get("/api/v1/report", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_text_checkin_saved_with_explanation(client):
    h = _register(client, "b@example.com")
    r = client.post("/api/v1/checkins", data={"text": "so tired, exams all week", "mood": "stressed"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["text_score"] == 68.0 and body["audio_score"] is None
    assert body["top_tokens"][0]["token"] == "exams"
    hist = client.get("/api/v1/checkins", headers=h).json()
    assert len(hist) == 1 and hist[0]["mood"] == "stressed"


def test_text_plus_voice_checkin_fuses_scores(client):
    h = _register(client, "c@example.com")
    r = client.post("/api/v1/checkins", data={"text": "feeling sad today"}, headers=h,
                    files={"audio": ("note.wav", _wav_bytes(), "audio/wav")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["audio_score"] == 40.0
    assert body["risk_score"] == pytest.approx(0.65 * 68 + 0.35 * 40, abs=0.01)
    assert body["voice"]["baseline_ready"] is False  # needs 3 earlier recordings


def test_voice_baseline_after_three_recordings(client):
    h = _register(client, "d@example.com")
    for _ in range(3):
        client.post("/api/v1/checkins", data={"text": "a normal day"}, headers=h,
                    files={"audio": ("n.wav", _wav_bytes(), "audio/wav")})
    r = client.post("/api/v1/checkins", headers=h, data={"text": "okay day"},
                    files={"audio": ("n.wav", _wav_bytes(), "audio/wav")})
    assert r.json()["voice"]["baseline_ready"] is True
    assert r.json()["voice"]["cues"]


def test_crisis_checkin_suggests_trusted_contact(client):
    h = _register(client, "e@example.com")
    client.patch("/api/v1/auth/me", headers=h, json={"trusted_contact_name": "Didi", "trusted_contact_phone": "+919999999999"})
    r = client.post("/api/v1/checkins", data={"text": "i want to end my life"}, headers=h).json()
    assert r["crisis_detected"] is True and r["risk_level"] == "CRITICAL"
    assert r["crisis_resources"] and r["suggest_contact"]["name"] == "Didi"


def test_private_mode_does_not_store_text(client):
    h = _register(client, "f@example.com")
    client.post("/api/v1/checkins", data={"text": "secret thoughts here", "save_text": "false"}, headers=h)
    assert client.get("/api/v1/checkins", headers=h).json()[0]["text"] is None


def test_empty_checkin_rejected(client):
    h = _register(client, "g@example.com")
    assert client.post("/api/v1/checkins", data={"text": ""}, headers=h).status_code == 422


def test_rising_trend_alert(client):
    from api.services import trend_alert
    assert trend_alert([40, 55, 70]) is not None
    assert trend_alert([70, 55, 40]) is None
    assert trend_alert([65, 62, 61, 70, 66]) is not None


def test_journal_and_safety_net(client):
    h = _register(client, "h@example.com")
    r = client.post("/api/v1/journal", headers=h, json={"content": "had a calm day", "mood": "thriving"}).json()
    assert r["risk_score"] is not None and r["crisis_resources"] is None
    r = client.post("/api/v1/journal", headers=h, json={"content": "i want to die", "analyse": False}).json()
    assert r["crisis_detected"] is True and r["crisis_resources"]
    assert len(client.get("/api/v1/journal", headers=h).json()) == 2


def test_phq9_scoring_and_item9(client):
    h = _register(client, "i@example.com")
    q = client.get("/api/v1/questionnaires/phq9").json()
    assert len(q["items"]) == 9
    r = client.post("/api/v1/questionnaires/phq9", headers=h, json={"answers": [1, 1, 1, 1, 1, 1, 1, 1, 0]}).json()
    assert r["score"] == 8 and r["severity"] == "mild" and r["crisis_detected"] is False
    r = client.post("/api/v1/questionnaires/phq9", headers=h, json={"answers": [0] * 8 + [1]}).json()
    assert r["crisis_detected"] is True
    r = client.post("/api/v1/questionnaires/gad7", headers=h, json={"answers": [3] * 7}).json()
    assert r["score"] == 21 and r["severity"] == "severe"
    assert client.post("/api/v1/questionnaires/gad7", headers=h, json={"answers": [1, 2]}).status_code == 422


def test_report_and_pdf(client):
    h = _register(client, "j@example.com")
    for text, mood in [("exams are hard", "stressed"), ("good day", "thriving"), ("tired again", "meh")]:
        client.post("/api/v1/checkins", headers=h, data={"text": text, "mood": mood})
    client.post("/api/v1/comfort/activity", headers=h, json={"kind": "breathing", "minutes": 2})
    r = client.get("/api/v1/report?days=30", headers=h).json()
    assert r["checkin_count"] == 3 and r["calm_minutes"] == 2
    assert {m["mood"] for m in r["mood_mix"]} == {"stressed", "thriving", "meh"}
    assert r["top_words"][0]["word"] == "exams"
    pdf = client.get("/api/v1/report/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_export_and_delete_account(client):
    h = _register(client, "k@example.com")
    client.post("/api/v1/checkins", headers=h, data={"text": "hello there"})
    data = client.get("/api/v1/me/data/export", headers=h).json()
    assert data["profile"]["email"] == "k@example.com" and len(data["checkins"]) == 1
    assert client.delete("/api/v1/me/data", headers=h).json()["deleted"] is True
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401


def test_risk_model_probabilities_returned(client):
    h = _register(client, "rm@example.com")
    body = client.post("/api/v1/checkins", data={"text": "so tired of exams"}, headers=h).json()
    assert body["emotion"] == "Mild Risk"
    assert body["probabilities"]["High Risk"] == 0.46


def test_works_without_voice_model(client):
    from api.state import models
    h = _register(client, "novoice@example.com")
    saved = {k: models.pop(k) for k in ("audio_model", "audio_scaler")}
    try:
        # voice-only: friendly 422 instead of a crash
        r = client.post("/api/v1/checkins", headers=h, files={"audio": ("n.wav", _wav_bytes(), "audio/wav")})
        assert r.status_code == 422
        # text + voice: text scored, voice score skipped, cues still measured
        r = client.post("/api/v1/checkins", headers=h, data={"text": "feeling sad today"},
                        files={"audio": ("n.wav", _wav_bytes(), "audio/wav")}).json()
        assert r["audio_score"] is None and r["text_score"] == 68.0
        assert r["voice_model_ready"] is False and r["voice"] is not None
        assert client.post("/api/v1/audio/analyse", files={"file": ("n.wav", _wav_bytes(), "audio/wav")}).status_code == 503
    finally:
        models.update(saved)


def test_text_model_missing_gives_503(client):
    from api.state import models
    h = _register(client, "notext@example.com")
    saved = {k: models.pop(k) for k in ("risk_tokenizer", "risk_model")}
    try:
        assert client.post("/api/v1/checkins", headers=h, data={"text": "hello there"}).status_code == 503
        assert client.post("/api/v1/text/analyse", json={"text": "hello there friend"}).status_code == 503
        # journal still saves, and the safety net still runs
        r = client.post("/api/v1/journal", headers=h, json={"content": "i want to die"}).json()
        assert r["risk_score"] is None and r["crisis_detected"] is True
    finally:
        models.update(saved)


def test_counsellor_sees_only_opted_in_users(client):
    shy = _register(client, "shy@example.com")
    open_ = _register(client, "open@example.com")
    client.patch("/api/v1/auth/me", headers=open_, json={"share_with_counsellor": True})
    for h in (shy, open_):
        client.post("/api/v1/checkins", headers=h, data={"text": "i want to kill myself"})
    assert client.get("/api/v1/counsellor/flagged", headers=shy).status_code == 403
    c = _register(client, "counsellor@college.edu")
    rows = client.get("/api/v1/counsellor/flagged", headers=c).json()
    assert len(rows) == 1 and rows[0]["student"].startswith("student-")
    assert "email" not in rows[0]
    assert client.patch(f"/api/v1/counsellor/flagged/{rows[0]['id']}", headers=c, json={"status": "contacted"}).json()["ok"]


def test_language_note_for_hindi_with_english_only_model(client):
    from api.state import models
    h = _register(client, "lang@example.com")
    models["risk_info"] = {"languages": ["en"]}
    r = client.post("/api/v1/checkins", headers=h, data={"text": "मैं बहुत परेशान हूँ, exams hain"}).json()
    assert r["language_note"] and "english" in r["language_note"]
    models["risk_info"] = {"languages": ["en", "hi", "hinglish"]}
    r = client.post("/api/v1/checkins", headers=h, data={"text": "मैं बहुत परेशान हूँ, exams hain"}).json()
    assert r["language_note"] is None
    assert client.get("/health").json()["languages"] == ["en", "hi", "hinglish"]
    models.pop("risk_info")


def test_hindi_crisis_triggers_support(client):
    h = _register(client, "hicrisis@example.com")
    r = client.post("/api/v1/checkins", headers=h, data={"text": "मैं अब जीना नहीं चाहता"}).json()
    assert r["crisis_detected"] is True and r["risk_level"] == "CRITICAL" and r["crisis_resources"]


def test_language_routing_between_two_models(client):
    from api.state import models
    h = _register(client, "route@example.com")
    models.update({"risk_info": {"languages": ["en", "hi", "hinglish"]},
                   "risk_tokenizer_en": "t_en", "risk_model_en": "m_en", "risk_info_en": {"languages": ["en"]}})
    try:
        def used(text):
            r = client.post("/api/v1/checkins", headers=h, data={"text": text}).json()
            return r["language"], r["model_used"], r["language_note"]
        assert used("i feel so tired of exams") == ("en", "english", None)
        assert used("yaar bahut stress hai exams ka") == ("hinglish", "multilingual", None)
        assert used("मैं बहुत परेशान हूँ") == ("hi", "multilingual", None)
        assert client.get("/health").json()["language_routing"] is True
    finally:
        for k in ("risk_info", "risk_tokenizer_en", "risk_model_en", "risk_info_en"):
            models.pop(k, None)


def test_no_routing_without_english_model(client):
    from api.state import models
    h = _register(client, "noroute@example.com")
    models["risk_info"] = {"languages": ["en", "hi", "hinglish"]}
    try:
        r = client.post("/api/v1/checkins", headers=h, data={"text": "i feel so tired of exams"}).json()
        assert r["model_used"] == "multilingual"
    finally:
        models.pop("risk_info")
