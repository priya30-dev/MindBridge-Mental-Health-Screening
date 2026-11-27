import numpy as np

try:  # works both as package import (src.fusion) and script import (fusion)
    from src.safety import CRISIS_SCORE_FLOOR, CRISIS_RESOURCES
except ImportError:  # pragma: no cover
    from safety import CRISIS_SCORE_FLOOR, CRISIS_RESOURCES

TEXT_WEIGHT = 0.65
AUDIO_WEIGHT = 0.35

RISK_LEVELS = {
    (0, 30): ("LOW", "#22C55E"),
    (30, 60): ("MEDIUM", "#F59E0B"),
    (60, 80): ("HIGH", "#F97316"),
    (80, 100): ("CRITICAL", "#EF4444"),
}

# Emotion -> risk weight. Single source of truth (was duplicated in
# api/routers/text.py and src/predict.py).
EMOTION_RISK_WEIGHTS = {
    "sadness": 0.85,
    "fear": 0.75,
    "anger": 0.65,
    "surprise": 0.35,
    "love": 0.15,
    "joy": 0.05,
}


def emotion_to_risk(text_result: dict) -> float:
    """Convert model output (emotion + confidence 0-100) to a 0-100 risk score."""
    emotion = text_result["emotion"]
    confidence = text_result["confidence"]
    weight = EMOTION_RISK_WEIGHTS.get(emotion, 0.5)
    return round(confidence * weight, 2)


def fuse_scores(text_score=None, audio_score=None, crisis_detected=False):
    """
    Combine text/audio scores (each 0-100) into one risk report.

    If crisis_detected is True (explicit self-harm language from
    src.safety), the score is floored at CRISIS_SCORE_FLOOR so it can never
    be reported as LOW/MEDIUM.
    """
    if text_score is None and audio_score is None:
        raise ValueError("At least one of text_score or audio_score is required")

    if text_score is not None and audio_score is not None:
        combined = TEXT_WEIGHT * text_score + AUDIO_WEIGHT * audio_score
    elif text_score is not None:
        combined = text_score
    else:
        combined = audio_score

    if crisis_detected:
        combined = max(combined, CRISIS_SCORE_FLOOR)

    combined = float(np.clip(combined, 0, 100))

    level = "LOW"
    color = "#22C55E"

    for (lo, hi), (lv, col) in RISK_LEVELS.items():
        if lo <= combined < hi or (hi == 100 and combined == 100):
            level = lv
            color = col
            break

    flags = []

    if crisis_detected:
        flags.append("CRISIS_LANGUAGE_DETECTED")

    if combined >= 80:
        flags.append("IMMEDIATE_REVIEW_REQUIRED")

    if combined >= 60:
        flags.append("CLINICAL_CONSULTATION_ADVISED")

    if combined >= 30:
        flags.append("MONITORING_RECOMMENDED")

    show_resources = crisis_detected or combined >= 80

    return {
        "risk_score": round(combined, 2),
        "risk_level": level,
        "risk_color": color,
        "flags": flags,
        "text_score": round(text_score, 2) if text_score is not None else None,
        "audio_score": round(audio_score, 2) if audio_score is not None else None,
        "crisis_detected": bool(crisis_detected),
        "crisis_resources": CRISIS_RESOURCES if show_resources else None,
        "disclaimer": (
            "This is an algorithmic alert, not a clinical diagnosis. "
            "A qualified mental health professional should review all flagged cases."
        ),
    }


if __name__ == "__main__":
    print(fuse_scores(75, 60))
