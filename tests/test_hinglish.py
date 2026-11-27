import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import pytest
from src.hinglish import has_devanagari, to_hinglish
from src.risk_model import clean


@pytest.mark.parametrize("hindi,roman", [
    ("मैं बहुत परेशान हूँ", "main bahut pareshaan hoon"),
    ("मुझे नींद नहीं आती", "mujhe neend nahin aati"),
    ("मैं अकेला महसूस करता हूँ", "main akela mahsoos karta hoon"),
    ("क्या करूँ, कुछ समझ नहीं आ रहा", "kya karoon, kuchh samajh nahin aa raha"),
    ("कल मेरा exam था", "kal mera exam tha"),
])
def test_to_hinglish(hindi, roman):
    assert to_hinglish(hindi) == roman


def test_has_devanagari():
    assert has_devanagari("exam की tension") and not has_devanagari("exam ki tension")


def test_clean_keeps_hindi_vowel_signs():
    assert clean("मैं बहुत परेशान हूँ!! https://x.com") == "मैं बहुत परेशान हूँ!!"


from src.hinglish import detect_language


@pytest.mark.parametrize("text,lang", [
    ("मैं बहुत परेशान हूँ", "hi"),
    ("exam की tension है", "hi"),
    ("yaar exams ki wajah se bahut stress hai", "hinglish"),
    ("aaj ka din accha tha", "hinglish"),
    ("mujhe neend nahi aati", "hinglish"),
    ("kuch samajh nahi aa raha, i feel so lost", "hinglish"),
    ("i feel so tired and stressed about exams", "en"),
    ("had a really nice day with my friends", "en"),
    ("the main problem is i cannot sleep at night", "en"),
    ("i want to go home to my family", "en"),
    ("", "en"),
])
def test_detect_language(text, lang):
    assert detect_language(text) == lang
