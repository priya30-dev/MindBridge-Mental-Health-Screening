"""Load whichever trained models are present. Nothing here crashes the API
if a model folder is missing: that feature is just switched off."""

import os


def fetch_from_hub(local_dir: str, repo_env: str) -> None:
    """If <repo_env> names a Hugging Face model repo (e.g. priya30-dev/mindbridge-risk-muril)
    and <local_dir> has no model yet, download it there. Used on the online server."""
    repo_id = os.getenv(repo_env, "").strip()
    if not repo_id or os.path.isfile(os.path.join(local_dir, "config.json")):
        return
    from huggingface_hub import snapshot_download

    print(f"Downloading {repo_id} from Hugging Face into {local_dir} ...", flush=True)
    snapshot_download(repo_id=repo_id, local_dir=local_dir, token=os.getenv("HF_TOKEN") or None)


def load_available_models() -> dict:
    loaded = {}
    from src.risk_model import RISK_MODEL_DIR

    fetch_from_hub(RISK_MODEL_DIR, "RISK_MODEL_REPO")
    fetch_from_hub(os.getenv("RISK_MODEL_DIR_EN", "./model_english"), "RISK_MODEL_REPO_EN")

    # 1) Text: prefer the 3-level risk model (./model), fall back to the old emotion model
    from src.risk_model import RISK_MODEL_DIR, load_risk_model, model_info, risk_model_available

    if risk_model_available():
        info = model_info()
        print(f"Loading risk model from {RISK_MODEL_DIR} "
              f"({info.get('base_model')}, languages: {', '.join(info.get('languages', ['en']))}) ...")
        loaded["risk_tokenizer"], loaded["risk_model"] = load_risk_model()
        loaded["risk_info"] = info

        # Optional English specialist next to a multilingual main model:
        # English check-ins go to it, Hindi/Hinglish to the main model.
        en_dir = os.getenv("RISK_MODEL_DIR_EN", "./model_english")
        use_routing = os.getenv("LANGUAGE_ROUTING", "1") == "1"
        if use_routing and "hi" in info.get("languages", []) and risk_model_available(en_dir):
            en_info = model_info(en_dir)
            print(f"Loading English model from {en_dir} ({en_info.get('base_model')}) — "
                  "English check-ins will use it, Hindi/Hinglish the main model ...")
            loaded["risk_tokenizer_en"], loaded["risk_model_en"] = load_risk_model(en_dir)
            loaded["risk_info_en"] = en_info
    else:
        text_path = os.getenv("TEXT_MODEL_PATH", "./models/roberta_finetuned")
        if os.path.isfile(os.path.join(text_path, "config.json")):
            from src.text_model import load_text_model

            print(f"Loading emotion model from {text_path} ...")
            loaded["tokenizer"], loaded["text_model"] = load_text_model(text_path)
        else:
            print(f"WARNING: no text model found (looked in {RISK_MODEL_DIR} and {text_path}). "
                  "Run prepare_data.py + train.py, then put the model folder there.")

    # 2) Voice: optional
    audio_path = os.getenv("AUDIO_MODEL_PATH", "./models/audio_cnn.pt")
    scaler_path = os.getenv("AUDIO_SCALER_PATH", "./models/audio_scaler.pkl")
    if os.path.isfile(audio_path) and os.path.isfile(scaler_path):
        from src.audio_model import load_audio_model

        print("Loading voice model ...")
        loaded["audio_model"], loaded["audio_scaler"] = load_audio_model()
    else:
        print("Voice model not found: voice notes will still get 'how you sounded' cues "
              "and speech-to-text, but no voice score.")

    names = {"risk_model": "risk_model", "risk_model_en": "risk_model_en (english)",
             "text_model": "text_model (emotion)", "audio_model": "audio_model"}
    print("Models ready:", ", ".join(v for k, v in names.items() if k in loaded) or "none")
    return loaded
