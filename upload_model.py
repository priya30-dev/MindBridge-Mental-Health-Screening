# ─────────────────────────────────────────────────────────────
# upload_model.py — put your trained models on Hugging Face
# Run (from the project folder, with venv active):   python upload_model.py
#
# It asks for your Hugging Face WRITE token (typing is hidden, nothing is saved),
# finds your username, and uploads:
#   ./model          → <you>/mindbridge-risk-muril     (or -roberta, from model_info.json)
#   ./model_english  → <you>/mindbridge-risk-roberta   (if the folder exists)
# Each gets a model card with your test scores. Repo names are saved to
# deploy_config.json so deploy_api.py can use them.
# ─────────────────────────────────────────────────────────────

import getpass
import json
import os

from huggingface_hub import HfApi

FOLDERS = [("model", "RISK_MODEL_REPO"), ("model_english", "RISK_MODEL_REPO_EN")]
CONFIG_FILE = "deploy_config.json"


def info_for(folder: str) -> dict:
    path = os.path.join(folder, "model_info.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"base_model": "roberta-base", "languages": ["en"]}


def repo_name(info: dict) -> str:
    base = info.get("base_model", "roberta-base").lower()
    return "mindbridge-risk-muril" if "muril" in base else "mindbridge-risk-roberta"


def model_card(info: dict, metrics: str) -> str:
    langs = info.get("languages", ["en"])
    lang_tags = "\n".join(f"- {l}" for l in langs if l in ("en", "hi"))
    lang_text = {"en": "English", "hi": "Hindi (Devanagari)", "hinglish": "Hinglish (romanised Hindi)"}
    return f"""---
language:
{lang_tags}
pipeline_tag: text-classification
base_model: {info.get('base_model', 'roberta-base')}
tags:
- mental-health
- text-classification
- risk-detection
---

# MindBridge risk classifier ({info.get('base_model')})

Classifies a short post as **No Signal / Mild Risk / High Risk** for mental-health
screening. Part of [MindBridge](https://github.com/priya30-dev/MindBridge-Mental-Health-Screening).

**Languages:** {', '.join(lang_text.get(l, l) for l in langs)}

> ⚠️ A screening aid, not a diagnosis. Do not use it as the only safety check:
> MindBridge pairs it with a rule-based crisis-language detector and shows helplines
> (India: Tele-MANAS 14416, 112 in an emergency).

## How MindBridge uses it
Risk score (0–100) = 100 × (0.5 × P(Mild) + 1.0 × P(High)).
Text is lower-cased and cleaned the same way as in training (`src/risk_model.clean`).

## Training data
[gokulan006/risk-analysis-dataset](https://huggingface.co/datasets/gokulan006/risk-analysis-dataset)
(built from the Kaggle datasets "Sentiment Analysis for Mental Health" and "Suicidal Tweet
Detection"; check their licenses). Hindi/Hinglish examples, if listed above, were
machine-translated with Helsinki-NLP/opus-mt-en-hi and romanised — their scores measure
translated text, not native posts.

## Test results
```
{metrics.strip()}
```

## Limitations
Social-media style English data; may miss sarcasm, indirect language, or cultural context.
Not validated clinically.
"""


def upload_with_retries(api, repo_id: str, folder: str, attempts: int = 5) -> None:
    """Big files over home internet can drop mid-way. upload_large_folder (newer
    huggingface_hub) resumes where it stopped; otherwise retry the normal upload."""
    import time

    ignore = ["*.zip", "__pycache__/*", ".cache/*"]
    for attempt in range(1, attempts + 1):
        try:
            if hasattr(api, "upload_large_folder"):
                api.upload_large_folder(repo_id=repo_id, folder_path=folder, repo_type="model",
                                        ignore_patterns=ignore)
            else:
                api.upload_folder(repo_id=repo_id, folder_path=folder, repo_type="model",
                                  ignore_patterns=ignore, commit_message="Upload MindBridge risk model")
            return
        except Exception as e:  # network drop, timeout, ...
            if attempt == attempts:
                raise
            wait = 15 * attempt
            print(f"\n  Upload interrupted ({type(e).__name__}). Retrying in {wait}s "
                  f"(attempt {attempt + 1}/{attempts}) ...", flush=True)
            time.sleep(wait)


def main():
    token = os.getenv("HF_TOKEN") or getpass.getpass("Paste your Hugging Face WRITE token (hidden), then Enter: ").strip()
    api = HfApi(token=token)
    user = api.whoami()["name"]
    print(f"Logged in as {user}\n")

    config = {}
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = json.load(f)

    for folder, key in FOLDERS:
        if not os.path.isfile(os.path.join(folder, "config.json")):
            print(f"- skipping ./{folder} (no model there)")
            continue
        info = info_for(folder)
        repo_id = f"{user}/{repo_name(info)}"
        metrics_path = os.path.join(folder, "metrics.txt")
        metrics = open(metrics_path, encoding="utf-8").read() if os.path.isfile(metrics_path) else "(not available)"
        with open(os.path.join(folder, "README.md"), "w", encoding="utf-8") as f:
            f.write(model_card(info, metrics))

        print(f"Uploading ./{folder} → https://huggingface.co/{repo_id}  (a few minutes for ~1 GB) ...", flush=True)
        api.create_repo(repo_id, repo_type="model", exist_ok=True, private=False)
        upload_with_retries(api, repo_id, folder)
        config[key] = repo_id
        print(f"  ✓ done: https://huggingface.co/{repo_id}\n")

    config["hf_user"] = user
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"Saved repo names to {CONFIG_FILE}. Next → python deploy_api.py")


if __name__ == "__main__":
    main()