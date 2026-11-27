"""Analysis helpers shared by the check-in and journal endpoints."""

import os
from statistics import mean

from api.state import models
from src.fusion import emotion_to_risk, fuse_scores
from src.safety import detect_crisis_language

# ── Text ──────────────────────────────────────────────────────────────────────

class ModelUnavailable(Exception):
    pass


def text_model_ready() -> bool:
    return "risk_model" in models or "text_model" in models


def voice_model_ready() -> bool:
    return "audio_model" in models


def model_languages() -> list[str]:
    if "risk_model" in models:
        return list(models.get("risk_info", {}).get("languages", ["en"]))
    return ["en"] if "text_model" in models else []


def pick_risk_model(lang: str):
    """English → English specialist (if loaded); Hindi/Hinglish → main model."""
    if lang == "en" and "risk_model_en" in models:
        return models["risk_tokenizer_en"], models["risk_model_en"], models.get("risk_info_en", {}), "english"
    info = models.get("risk_info", {})
    name = "multilingual" if "hi" in info.get("languages", []) else "english"
    return models["risk_tokenizer"], models["risk_model"], info, name


def language_note(lang: str, model_langs: list[str]) -> str | None:
    if lang == "hi" and "hi" not in model_langs:
        return ("mindbridge's current model mostly understands english, so this score may be off. "
                "your words were still checked for crisis signs in hindi.")
    return None


def analyse_text(text: str, explain: bool = False) -> dict:
    from src.hinglish import detect_language

    lang = detect_language(text)
    out = {"top_words": [], "crisis": detect_crisis_language(text), "language": lang}

    if "risk_model" in models:  # 3-level risk model trained with train.py
        from src.risk_model import explain_risk, predict_risk

        tok, model, info, model_name = pick_risk_model(lang)
        result = predict_risk(text, tok, model)
        out.update(text_score=result["risk_score"], emotion=result["label_name"],
                   probabilities=result["probabilities"], model_used=model_name,
                   language_note=language_note(lang, info.get("languages", ["en"])))
        if explain:
            out["top_words"] = explain_risk(text, tok, model)["top_tokens"]
        return out

    out["language_note"] = language_note(lang, model_languages())

    if "text_model" in models:  # legacy 6-emotion model
        from src.text_model import predict_text

        result = predict_text(text, models["tokenizer"], models["text_model"])
        out.update(text_score=emotion_to_risk(result), emotion=result["emotion"], probabilities=None)
        if explain:
            from src.explainer import explain_text

            exp = explain_text(text=text, tokenizer=models["tokenizer"],
                               model=models["text_model"], target_class=result["label"])
            out["top_words"] = exp["top_tokens"]
        return out

    raise ModelUnavailable("The text model isn't loaded on the server yet.")


# ── Voice ─────────────────────────────────────────────────────────────────────

def audio_stats(path: str) -> dict:
    """Simple, explainable voice measurements used for 'how you sounded'."""
    import librosa
    import numpy as np

    y, sr = librosa.load(path, sr=16000, mono=True)
    duration = len(y) / sr if sr else 0.0
    if duration < 0.5:
        return {"duration": round(duration, 2), "energy": 0.0, "pitch_var": 0.0, "pause_ratio": 1.0}
    energy = float(np.mean(librosa.feature.rms(y=y)))
    voiced = librosa.effects.split(y, top_db=30)
    voiced_len = sum(int(e - s) for s, e in voiced)
    pause_ratio = 1 - voiced_len / len(y)
    try:
        f0 = librosa.yin(y, fmin=65, fmax=400, sr=sr)
        f0 = f0[np.isfinite(f0)]
        pitch_var = float(np.std(f0)) if f0.size else 0.0
    except Exception:
        pitch_var = 0.0
    return {"duration": round(duration, 2), "energy": round(energy, 5),
            "pitch_var": round(pitch_var, 2), "pause_ratio": round(float(pause_ratio), 3)}


def analyse_audio(path: str) -> dict:
    """Voice score needs the trained voice model; the 'how you sounded'
    measurements work without it."""
    score = None
    if voice_model_ready():
        from src.audio_model import predict_audio_features
        from src.utils import extract_audio_features

        feats = extract_audio_features(path)
        score = predict_audio_features(feats, models["audio_model"], models["audio_scaler"])["risk_score"]
    return {"audio_score": score, "stats": audio_stats(path)}


def transcription_enabled() -> bool:
    return os.getenv("TRANSCRIBE", "0") == "1"


def warm_up():
    """Run the slow first-time work (audio library compile, explainer setup)
    once at startup, so the first real check-in isn't the slow one."""
    import tempfile

    try:
        import numpy as np
        import soundfile as sf

        sr = 16000
        t = np.linspace(0, 1, sr, endpoint=False)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, (0.2 * np.sin(2 * np.pi * 200 * t)).astype("float32"), sr)
        audio_stats(tmp.name)
        os.unlink(tmp.name)
    except Exception as e:  # warm-up must never stop the server
        print("audio warm-up skipped:", e)
    try:
        if text_model_ready():
            analyse_text("warming up the model", explain=os.getenv("WARMUP_EXPLAIN", "1") == "1")
    except Exception as e:
        print("text warm-up skipped:", e)
    print("Warm-up done: first check-in will be fast.")


_whisper = None

def transcribe(path: str) -> str | None:
    """Speech-to-text with faster-whisper if installed and TRANSCRIBE=1.
    Lets a voice-only check-in also get text analysis + the safety check."""
    global _whisper
    if os.getenv("TRANSCRIBE", "0") != "1":
        return None
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    if _whisper is None:
        _whisper = WhisperModel(os.getenv("WHISPER_SIZE", "base"), compute_type="int8")
    segments, _ = _whisper.transcribe(path)
    text = " ".join(s.text.strip() for s in segments).strip()
    return text or None


MIN_BASELINE = 3

def audio_cues(stats: dict, history: list[dict]) -> dict:
    """Compare this recording with the user's own past recordings.
    No universal thresholds: 'lower energy' means lower than *your* usual."""
    if len(history) < MIN_BASELINE:
        return {"baseline_ready": False, "baseline_count": len(history), "cues": []}

    def avg(key):
        vals = [h.get(key, 0) for h in history if h.get(key)]
        return mean(vals) if vals else 0

    cues = []
    e, p, pr = avg("energy"), avg("pitch_var"), avg("pause_ratio")
    if e and stats["energy"] < 0.8 * e:
        cues.append({"label": "lower energy than usual", "direction": "risk-increasing"})
    elif e and stats["energy"] > 1.25 * e:
        cues.append({"label": "more energy than usual", "direction": "risk-reducing"})
    if p and stats["pitch_var"] < 0.75 * p:
        cues.append({"label": "flatter tone than usual", "direction": "risk-increasing"})
    else:
        cues.append({"label": "usual tone", "direction": "risk-reducing"})
    if pr and stats["pause_ratio"] > pr + 0.1:
        cues.append({"label": "more pauses than usual", "direction": "risk-increasing"})
    else:
        cues.append({"label": "steady pace", "direction": "risk-reducing"})
    return {"baseline_ready": True, "baseline_count": len(history), "cues": cues}


# ── Trends ────────────────────────────────────────────────────────────────────

def trend_alert(recent_scores: list[float]) -> str | None:
    """recent_scores: oldest → newest, including the current check-in."""
    if len(recent_scores) >= 3:
        a, b, c = recent_scores[-3:]
        if a < b < c and c >= 60:
            return ("your last three check-ins have been getting heavier. "
                    "this might be a good time to talk to someone you trust or a counsellor.")
    last7 = recent_scores[-7:]
    if len(last7) >= 5 and mean(last7) >= 60:
        return ("things have felt heavy for a while now. you don't have to wait for it to get worse "
                "to reach out — a counsellor can help.")
    return None


def combine(text_part: dict | None, audio_part: dict | None) -> dict:
    crisis = bool(text_part and text_part["crisis"]["crisis_detected"])
    return fuse_scores(
        text_score=text_part["text_score"] if text_part else None,
        audio_score=audio_part["audio_score"] if audio_part else None,
        crisis_detected=crisis,
    )

