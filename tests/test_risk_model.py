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


def test_fetch_from_hub_only_when_needed(tmp_path, monkeypatch):
    import huggingface_hub
    from src import model_loader
    calls = []
    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda **kw: calls.append(kw), raising=False)
    # no repo configured -> nothing happens
    monkeypatch.delenv("RISK_MODEL_REPO", raising=False)
    model_loader.fetch_from_hub(str(tmp_path / "m"), "RISK_MODEL_REPO")
    assert calls == []
    # repo configured and folder empty -> download
    monkeypatch.setenv("RISK_MODEL_REPO", "priya30-dev/mindbridge-risk-muril")
    model_loader.fetch_from_hub(str(tmp_path / "m"), "RISK_MODEL_REPO")
    assert calls[0]["repo_id"] == "priya30-dev/mindbridge-risk-muril"
    # model already there -> no second download
    (tmp_path / "m").mkdir()
    (tmp_path / "m" / "config.json").write_text("{}")
    model_loader.fetch_from_hub(str(tmp_path / "m"), "RISK_MODEL_REPO")
    assert len(calls) == 1
