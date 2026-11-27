import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import pytest
from src.safety import detect_crisis_language


@pytest.mark.parametrize(
    "text",
    [
        "I want to kill myself",
        "I think everyone would be better off without me",
        "I'm planning on ending it all tonight",
        "Sometimes I feel suicidal",
        "I don't want to live anymore",
        "I've been self-harming again",
        "There is no point in living",
        "I can't go on like this",
        "ab jeena nahi hai",
    ],
)
def test_crisis_language_is_detected(text):
    assert detect_crisis_language(text)["crisis_detected"] is True


@pytest.mark.parametrize(
    "text",
    [
        "Had a great weekend with friends!",          # 'end' inside 'weekend'
        "The movie had a sad ending but I loved it",
        "I'm dying to try that new cafe",
        "Let's end the meeting early today",
        "I feel tired and a bit stressed about exams",
        "",
    ],
)
def test_safe_text_is_not_flagged(text):
    assert detect_crisis_language(text)["crisis_detected"] is False


def test_matched_phrases_are_returned():
    result = detect_crisis_language("I want to die, I can't go on")
    assert len(result["matched_phrases"]) == 2


# ── Hindi + Hinglish ─────────────────────────────────────────
@pytest.mark.parametrize(
    "text",
    [
        "मैं मरना चाहता हूँ",
        "मैं मरना चाहती हूं",
        "अब जीना नहीं चाहता",
        "जीने का मन नहीं करता",
        "सोच रहा हूँ आत्महत्या कर लूं",
        "मैं ज़िंदगी खत्म करना चाहता हूँ",       # with nukta
        "मैं जिंदगी खत्म करना चाहता हूं",        # without nukta
        "खुद को नुकसान पहुँचाने का मन करता है",
        "बस मर जाऊं",
        "main marna chahta hoon",
        "jeene ka mann nahi karta yaar",
        "khud ko khatam kar dunga",
        "zindagi khatam karni hai",
        "sab khatam kar dungi aaj",
        "apni jaan le lungi",
    ],
)
def test_hindi_hinglish_crisis_detected(text):
    assert detect_crisis_language(text)["crisis_detected"] is True


@pytest.mark.parametrize(
    "text",
    [
        "मैं आज बहुत खुश हूँ",
        "दोस्तों के साथ मज़ा आया",
        "परीक्षा की वजह से थोड़ा तनाव है",
        "ज़िंदगी में बहुत कुछ सीखना है",
        "aaj ka din accha tha",
        "exam ki tension hai thodi",
        "usne goal maar diya",
        "zindagi mast chal rahi hai",
    ],
)
def test_everyday_hindi_hinglish_not_flagged(text):
    assert detect_crisis_language(text)["crisis_detected"] is False
