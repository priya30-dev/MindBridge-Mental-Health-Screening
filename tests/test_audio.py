import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pytest

sf = pytest.importorskip("soundfile")
pytest.importorskip("librosa")
pytest.importorskip("datasets")  # src.utils imports it

from src.utils import extract_audio_features  # noqa: E402


@pytest.fixture
def tone_wav(tmp_path):
    """2-second 220 Hz tone with slight noise, so trimming keeps it."""
    sr = 16000
    t = np.linspace(0, 2, 2 * sr, endpoint=False)
    rng = np.random.default_rng(0)
    y = 0.5 * np.sin(2 * np.pi * 220 * t) + 0.01 * rng.standard_normal(t.size)
    path = tmp_path / "tone.wav"
    sf.write(path, y.astype(np.float32), sr)
    return str(path)


def test_feature_vector_shape(tone_wav):
    feats = extract_audio_features(tone_wav)
    assert feats.ndim == 1
    assert feats.shape[0] == 122


def test_features_are_finite(tone_wav):
    feats = extract_audio_features(tone_wav)
    assert np.all(np.isfinite(feats))
