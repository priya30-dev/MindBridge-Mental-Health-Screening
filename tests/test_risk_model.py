import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import pytest
from src.risk_model import clean, probs_to_score, risk_model_available


def test_clean_matches_training_preprocessing():
    assert clean("I can't DO this anymore!! https://x.com @friend") == "i can't do this anymore!!"
    assert clean("  lots   of\n spaces ") == "lots of spaces"


@pytest.mark.parametrize("probs,expected", [
    ([1, 0, 0], 0), ([0, 1, 0], 50), ([0, 0, 1], 100), ([0.2, 0.4, 0.4], 60),
])
def test_probs_to_score(probs, expected):
    assert probs_to_score(probs) == pytest.approx(expected)


def test_missing_model_folder_detected(tmp_path):
    assert risk_model_available(str(tmp_path)) is False
    (tmp_path / "config.json").write_text("{}")
    assert risk_model_available(str(tmp_path)) is True
