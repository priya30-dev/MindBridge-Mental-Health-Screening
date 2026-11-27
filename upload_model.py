# ─────────────────────────────────────────────────────────────
# upload_model.py — Push trained model to HuggingFace Hub
# Run AFTER training: python upload_model.py
#
# Prerequisites:
#   pip install huggingface_hub
#   huggingface-cli login   ← run this first, paste your HF token
# ─────────────────────────────────────────────────────────────

from huggingface_hub import HfApi
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import os

# ── CHANGE THIS to your HuggingFace username ──────────────────
HF_USERNAME  = "your-hf-username"
REPO_NAME    = "mindbridge-roberta-lite"
MODEL_DIR    = "./model"

REPO_ID = f"{HF_USERNAME}/{REPO_NAME}"


def upload():
    print(f"Uploading model to: {REPO_ID}")

    tok   = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

    # Push to hub (creates repo if it doesn't exist)
    tok.push_to_hub(REPO_ID, private=False)
    model.push_to_hub(REPO_ID, private=False)

    print(f"\n✓ Model uploaded!")
    print(f"  URL: https://huggingface.co/{REPO_ID}")
    print(f"\n  Now update MODEL_DIR in predict.py to:")
    print(f"  MODEL_DIR = '{REPO_ID}'")
    print(f"\n  This allows Streamlit Cloud to load the model without storing it locally.")


if __name__ == "__main__":
    upload()
