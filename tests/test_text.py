import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import pytest
from src.text_model import load_text_model, predict_text


@pytest.fixture(scope="module")
def text_pipeline():
    return load_text_model()


@pytest.mark.parametrize(
    "text",
    [
        "I had a great day today!",
        "I feel overwhelmed and hopeless all the time.",
        "I want to end my life, nothing matters anymore.",
    ],
)
def test_predict_text_output_format(text_pipeline, text):
    tokenizer, model = text_pipeline
    result = predict_text(text, tokenizer, model)

    assert "label" in result
    assert "emotion" in result
    assert "confidence" in result
    assert "probabilities" in result


def test_confidence_range(text_pipeline):
    tokenizer, model = text_pipeline
    result = predict_text("test input text here", tokenizer, model)

    assert 0 <= result["confidence"] <= 100


def test_probabilities_format(text_pipeline):
    tokenizer, model = text_pipeline
    result = predict_text("I feel okay today.", tokenizer, model)

    assert isinstance(result["probabilities"], list)
    assert len(result["probabilities"]) == 6