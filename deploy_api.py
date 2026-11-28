# ─────────────────────────────────────────────────────────────
# deploy_api.py — put the MindBridge API online as a Hugging Face Space
# Run AFTER upload_model.py:   python deploy_api.py
#
# It asks (hidden typing, nothing saved to disk or git) for:
#   • your Hugging Face WRITE token
#   • your Neon connection string (postgresql://...)
# Then it creates/updates the Space <you>/mindbridge-api, stores the Neon link and a
# fresh SECRET_KEY as Space *secrets*, points it at your uploaded models, and uploads
# the API code. Hugging Face then builds and starts it (~10-15 min the first time).
#
#   python deploy_api.py --dry-run     # just show which files would be uploaded
# ─────────────────────────────────────────────────────────────

import argparse
import getpass
import json
import os
import re
import secrets
import shutil
import tempfile

CONFIG_FILE = "deploy_config.json"
SPACE_NAME = "mindbridge-api"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.db")


def build_staging() -> str:
    """Everything the Space needs, laid out at its root."""
    stage = tempfile.mkdtemp(prefix="mindbridge_space_")
    shutil.copytree("api", os.path.join(stage, "api"), ignore=IGNORE)
    shutil.copytree("src", os.path.join(stage, "src"), ignore=IGNORE)
    for name in ("Dockerfile", "requirements.txt", "README.md"):
        shutil.copy(os.path.join("deploy", "space", name), os.path.join(stage, name))
    return stage


def space_host(space_id: str) -> str:
    """priya30-dev/mindbridge-api -> https://priya30-dev-mindbridge-api.hf.space"""
    return "https://" + re.sub(r"[^a-z0-9-]", "-", space_id.lower().replace("/", "-")) + ".hf.space"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="list the files, don't upload anything")
    ap.add_argument("--new-secret-key", action="store_true", help="rotate SECRET_KEY (logs everyone out)")
    args = ap.parse_args()

    stage = build_staging()
    files = sorted(os.path.relpath(os.path.join(r, f), stage) for r, _, fs in os.walk(stage) for f in fs)
    print("Files for the Space:\n  " + "\n  ".join(f.replace(os.sep, "/") for f in files) + "\n")
    if args.dry_run:
        shutil.rmtree(stage)
        return

    config = json.load(open(CONFIG_FILE, encoding="utf-8")) if os.path.isfile(CONFIG_FILE) else {}
    if not config.get("RISK_MODEL_REPO"):
        raise SystemExit("No uploaded model found in deploy_config.json — run  python upload_model.py  first.")

    from huggingface_hub import HfApi

    token = os.getenv("HF_TOKEN") or getpass.getpass("Paste your Hugging Face WRITE token (hidden), then Enter: ").strip()
    api = HfApi(token=token)
    user = api.whoami()["name"]
    space_id = f"{user}/{SPACE_NAME}"

    db_url = os.getenv("DATABASE_URL") or getpass.getpass(
        "Paste your Neon connection string (hidden, starts with postgresql://), then Enter\n"
        "(or just press Enter to use a temporary SQLite database): ").strip()
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]
    if db_url and not db_url.startswith("postgresql://"):
        raise SystemExit("That doesn't look like a Neon connection string (it should start with postgresql://).")

    is_new = not api.repo_exists(space_id, repo_type="space")
    print(f"\n{'Creating' if is_new else 'Updating'} Space https://huggingface.co/spaces/{space_id} ...", flush=True)
    api.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True, private=False)

    # Secrets: hidden on Hugging Face, available to the app as environment variables
    if db_url:
        api.add_space_secret(space_id, "DATABASE_URL", db_url)
    if is_new or args.new_secret_key:
        api.add_space_secret(space_id, "SECRET_KEY", secrets.token_hex(32))
    # Plain settings
    variables = {
        "RISK_MODEL_REPO": config["RISK_MODEL_REPO"],
        "LANGUAGE_ROUTING": "1",
        "AUTH_RATE_LIMIT": "20",
        "SHAP_MAX_EVALS": "80",
    }
    if config.get("RISK_MODEL_REPO_EN"):
        variables["RISK_MODEL_REPO_EN"] = config["RISK_MODEL_REPO_EN"]
    for key, value in variables.items():
        api.add_space_variable(space_id, key, value)

    print("Uploading the API code ...", flush=True)
    api.upload_folder(repo_id=space_id, repo_type="space", folder_path=stage,
                      commit_message="Deploy MindBridge API")
    shutil.rmtree(stage)

    api_base = space_host(space_id) + "/api/v1"
    config.update(space_id=space_id, api_base=api_base)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"""
✓ Uploaded. Hugging Face is now building your server (first time ~10-15 min).
  Watch it:      https://huggingface.co/spaces/{space_id}   (click "Logs")
  When it says "Running", check:  {space_host(space_id)}/health

  Your API address for the Streamlit dashboard:
      API_BASE = "{api_base}"
""")


if __name__ == "__main__":
    main()
