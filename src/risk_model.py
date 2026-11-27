"""
3-level mental health risk classifier (No Signal / Mild Risk / High Risk).

Trained with train.py on gokulan006/risk-analysis-dataset (see prepare_data.py).
Test-set results (4,350 posts): weighted F1 0.85, High Risk recall 0.76,
and 99% of High Risk posts flagged as at least Mild Risk.

The model folder (config.json, model.safetensors, tokenizer files) is found at
RISK_MODEL_DIR, default ./model
"""

import os
import re

import numpy as np

RISK_MODEL_DIR = os.getenv("RISK_MODEL_DIR", "./model")
LABELS = ["No Signal", "Mild Risk", "High Risk"]
MAX_LEN = 128  # same as training


def _device():
    import torch

    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def clean(text: str) -> str:
    """Exactly the cleaning used in prepare_data.py, so inference matches training."""
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    # keep Devanagari (U+0900-U+097F): Hindi vowel signs aren't "\w" and would be stripped
    text = re.sub(r"[^\w\s\u0900-\u097F.,!?'\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def risk_model_available(path: str | None = None) -> bool:
    return os.path.isfile(os.path.join(path or RISK_MODEL_DIR, "config.json"))


def model_info(path: str | None = None) -> dict:
    """model_info.json is written by train.py; older models don't have it."""
    import json

    f = os.path.join(path or RISK_MODEL_DIR, "model_info.json")
    if os.path.isfile(f):
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    return {"base_model": "roberta-base", "languages": ["en"]}


def _should_quantize(device) -> bool:
    mode = os.getenv("RISK_QUANTIZE", "auto").lower()
    return mode in ("1", "true", "yes") or (mode == "auto" and device.type == "cpu")


def quantize(model):
    """int8 dynamic quantization of the Linear layers: ~2x faster on CPU,
    ~4x smaller in memory, usually <1 point of accuracy lost.
    Check on your own data with:  python benchmark_model.py"""
    import torch

    try:
        from torch.ao.quantization import quantize_dynamic
    except ImportError:  # older torch
        from torch.quantization import quantize_dynamic
    return quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)


def load_risk_model(path: str | None = None, quantized: bool | None = None):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    path = path or RISK_MODEL_DIR
    try:
        tokenizer = AutoTokenizer.from_pretrained(path)
    except Exception as e:
        # A tokenizer.json saved by a newer `tokenizers` (e.g. on Colab) can't be
        # read by older versions. Fine-tuning never changes the tokenizer, so the
        # base model's tokenizer is identical.
        base = os.getenv("RISK_BASE_TOKENIZER") or model_info(path).get("base_model", "roberta-base")
        print(f"Couldn't read the tokenizer in {path} ({type(e).__name__}); "
              f"using the identical '{base}' tokenizer instead.")
        tokenizer = AutoTokenizer.from_pretrained(base)
    device = _device()
    model = AutoModelForSequenceClassification.from_pretrained(path).to(device)
    model.eval()
    if quantized if quantized is not None else _should_quantize(device):
        model = quantize(model)
        print("Risk model quantized to int8 for faster CPU predictions "
              "(set RISK_QUANTIZE=0 in .env to turn off).")
    return tokenizer, model


def _probs(texts: list[str], tokenizer, model) -> np.ndarray:
    import torch

    device = next(model.parameters()).device
    enc = tokenizer([clean(t) for t in texts], max_length=MAX_LEN, padding=True,
                    truncation=True, return_tensors="pt")
    enc = {k: v.to(device) for k, v in enc.items()}
    with torch.no_grad():
        logits = model(**enc).logits
    return torch.softmax(logits, dim=-1).cpu().numpy()


def probs_to_score(probs) -> float:
    """0-100 risk score: Mild counts half, High counts fully.
    e.g. confident Mild ≈ 50 (MEDIUM), confident High ≈ 100 (CRITICAL)."""
    return float(100 * (0.5 * probs[1] + 1.0 * probs[2]))


def predict_risk(text: str, tokenizer, model) -> dict:
    p = _probs([text], tokenizer, model)[0]
    label = int(np.argmax(p))
    return {
        "label": label,
        "label_name": LABELS[label],
        "probabilities": {name: round(float(v), 4) for name, v in zip(LABELS, p)},
        "risk_score": round(probs_to_score(p), 2),
    }


_explainers: dict = {}


def explain_risk(text: str, tokenizer, model, top_k: int = 5) -> dict:
    """SHAP on the risk score itself: positive = pushed risk up."""
    import shap

    _explainer = _explainers.get(id(model))
    if _explainer is None:
        def score_fn(texts):
            p = _probs(list(texts), tokenizer, model)
            return (100 * (0.5 * p[:, 1] + p[:, 2])).reshape(-1, 1)

        _explainer = _explainers[id(model)] = shap.Explainer(score_fn, tokenizer)

    # max_evals caps how many times the model runs (default 500 is slow on CPU)
    sv = _explainer([clean(text)], max_evals=int(os.getenv("SHAP_MAX_EVALS", "80")),
                    batch_size=int(os.getenv("SHAP_BATCH_SIZE", "16")))
    vals = sv.values[0]
    if vals.ndim == 2:
        vals = vals[:, 0]
    pairs = []
    for tok, val in zip(sv.data[0], vals):
        tok = str(tok).strip()
        if tok in ("<s>", "</s>", "<pad>", "") or not re.search(r"\w", tok):
            continue
        pairs.append((tok, float(val)))
    pairs.sort(key=lambda x: abs(x[1]), reverse=True)
    return {
        "top_tokens": [
            {"token": t, "shap_value": round(v, 4),
             "direction": "risk-increasing" if v > 0 else "risk-reducing"}
            for t, v in pairs[:top_k]
        ]
    }
