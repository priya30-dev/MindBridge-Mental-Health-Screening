# ─────────────────────────────────────────────────────────────
# predict.py — Inference + SHAP explainability
# Used by app.py — don't run this directly
# ─────────────────────────────────────────────────────────────

import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

MODEL_DIR = "./model"
DEVICE    = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Risk scoring ──────────────────────────────────────────────
#   Label 0 = No signal   → base risk 0
#   Label 1 = Mild risk   → base risk ~50
#   Label 2 = High risk   → base risk ~100
RISK_CONFIG = {
    0: {"label": "No Signal",  "color": "#22C55E", "emoji": "🟢"},
    1: {"label": "Mild Risk",  "color": "#F59E0B", "emoji": "🟡"},
    2: {"label": "High Risk",  "color": "#EF4444", "emoji": "🔴"},
}


# ── Load model (cached so Streamlit doesn't reload every run) ─
_cache = {}

def load_model():
    if "model" not in _cache:
        tok   = AutoTokenizer.from_pretrained(MODEL_DIR)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
        model.eval().to(DEVICE)
        _cache["tok"]   = tok
        _cache["model"] = model
    return _cache["tok"], _cache["model"]


# ── Predict ───────────────────────────────────────────────────
def predict(text: str) -> dict:
    tok, model = load_model()

    enc = tok(text, max_length=128, padding="max_length",
               truncation=True, return_tensors="pt")
    ids  = enc["input_ids"].to(DEVICE)
    mask = enc["attention_mask"].to(DEVICE)

    with torch.no_grad():
        logits = model(input_ids=ids, attention_mask=mask).logits
        probs  = torch.softmax(logits, dim=-1).cpu().numpy()[0]

    label = int(np.argmax(probs))

    # Risk score: weighted combination
    risk_score = float(probs[1] * 50 + probs[2] * 100)
    risk_score = round(min(risk_score, 100.0), 1)

    cfg = RISK_CONFIG[label]

    return {
        "label":       label,
        "risk_level":  cfg["label"],
        "risk_color":  cfg["color"],
        "risk_emoji":  cfg["emoji"],
        "risk_score":  risk_score,
        "probs":       {
            "no_signal": round(float(probs[0]) * 100, 1),
            "mild_risk": round(float(probs[1]) * 100, 1),
            "high_risk": round(float(probs[2]) * 100, 1),
        },
        "disclaimer": (
            "⚠ This is an algorithmic alert, not a clinical diagnosis. "
            "Always refer flagged cases to a qualified mental health professional."
        ),
    }


# ── SHAP explainability ───────────────────────────────────────
def explain(text: str, target_class: int = None) -> list[dict]:
    """
    Returns top-6 tokens with their SHAP values.
    target_class: which class to explain (defaults to predicted class)
    """
    import shap

    tok, model = load_model()

    # If target_class not given, use predicted class
    if target_class is None:
        result = predict(text)
        target_class = result["label"]
        # Always explain against high-risk class for safety
        if target_class == 0:
            target_class = 2

    def predict_fn(texts):
        enc = tok(list(texts), max_length=128, padding=True,
                  truncation=True, return_tensors="pt")
        with torch.no_grad():
            logits = model(**enc).logits
        return torch.softmax(logits, dim=-1).numpy()

    explainer   = shap.Explainer(predict_fn, tok)
    shap_values = explainer([text])

    # shape: (1, n_tokens, n_classes)
    vals   = shap_values.values[0, :, target_class]
    tokens = shap_values.data[0]

    pairs = [
        (tok_str, float(val))
        for tok_str, val in zip(tokens, vals)
        if tok_str not in ("<s>", "</s>", "<pad>", "Ġ")
        and len(tok_str.strip()) > 1
    ]

    # Sort by absolute contribution, take top 6
    pairs.sort(key=lambda x: abs(x[1]), reverse=True)
    top6 = pairs[:6]

    return [
        {
            "token":     t.replace("Ġ", ""),   # remove RoBERTa space prefix
            "value":     round(v, 4),
            "direction": "increases risk" if v > 0 else "reduces risk",
            "color":     "#FCA5A5" if v > 0 else "#86EFAC",
        }
        for t, v in top6
    ]
