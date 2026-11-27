import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import pytest
from src.fusion import fuse_scores, emotion_to_risk, CRISIS_SCORE_FLOOR


@pytest.mark.parametrize(
    "score,level",
    [(0, "LOW"), (29.9, "LOW"), (30, "MEDIUM"), (60, "HIGH"), (80, "CRITICAL"), (100, "CRITICAL")],
)
def test_risk_level_boundaries(score, level):
    assert fuse_scores(text_score=score)["risk_level"] == level


def test_weighted_fusion():
    result = fuse_scores(text_score=80, audio_score=40)
    assert result["risk_score"] == pytest.approx(0.65 * 80 + 0.35 * 40)


def test_audio_only_goes_in_audio_slot():
    result = fuse_scores(audio_score=70)
    assert result["text_score"] is None
    assert result["audio_score"] == 70
    assert result["risk_score"] == 70


def test_requires_at_least_one_score():
    with pytest.raises(ValueError):
        fuse_scores()


def test_crisis_floors_score_and_adds_resources():
    result = fuse_scores(text_score=10, crisis_detected=True)
    assert result["risk_score"] >= CRISIS_SCORE_FLOOR
    assert result["risk_level"] == "CRITICAL"
    assert "CRISIS_LANGUAGE_DETECTED" in result["flags"]
    assert result["crisis_resources"]


def test_no_resources_for_low_risk():
    result = fuse_scores(text_score=10)
    assert result["crisis_resources"] is None
    assert result["crisis_detected"] is False


def test_emotion_to_risk():
    assert emotion_to_risk({"emotion": "sadness", "confidence": 100}) == 85
    assert emotion_to_risk({"emotion": "joy", "confidence": 100}) == 5
    assert emotion_to_risk({"emotion": "unknown", "confidence": 50}) == 25
