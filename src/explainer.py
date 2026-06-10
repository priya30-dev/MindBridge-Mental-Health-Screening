import shap
import numpy as np
import torch

_explainer = None


def get_explainer(tokenizer, model):
    global _explainer

    if _explainer is None:

        def predict_fn(texts):
            encoding = tokenizer(
                list(texts),
                max_length=256,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )

            device = next(model.parameters()).device
            encoding = {k: v.to(device) for k, v in encoding.items()}

            with torch.no_grad():
                logits = model(**encoding).logits
                probs = torch.softmax(logits, dim=-1)

            return probs.cpu().numpy()

        _explainer = shap.Explainer(predict_fn, tokenizer)

    return _explainer


def explain_text(text: str, tokenizer, model, target_class: int = 1) -> dict:
    explainer = get_explainer(tokenizer, model)

    shap_values = explainer([text])

    values = shap_values.values

    if values.ndim == 3:
        vals = values[0, :, target_class]
    else:
        vals = values[0]

    tokens = shap_values.data[0]

    pairs = []

    for token, val in zip(tokens, vals):
        token = str(token).strip()

        if token in ["<s>", "</s>", "<pad>", "", " "]:
            continue

        pairs.append((token, float(val)))

    pairs.sort(key=lambda x: abs(x[1]), reverse=True)

    top5 = pairs[:5]

    return {
        "top_tokens": [
            {
                "token": token,
                "shap_value": round(value, 4),
                "direction": "risk-increasing" if value > 0 else "risk-reducing",
            }
            for token, value in top5
        ],
        "explanation_note": (
            "Tokens with positive SHAP values pushed the model toward high-risk; "
            "negative values pushed it away."
        ),
    }