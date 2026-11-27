# ─────────────────────────────────────────────────────────────
# Step 1 of 4 — Download & prepare the dataset
# Run: python prepare_data.py
# Time: ~2-5 minutes
#
# Dataset: gokulan006/risk-analysis-dataset (Hugging Face)
#   ~48k social media posts labelled with 3 mental health risk levels.
#   Built from two Kaggle datasets ("Sentiment Analysis for Mental Health"
#   and "Suicidal Tweet Detection") — check their licenses before any
#   commercial use.
# ─────────────────────────────────────────────────────────────

import os
import re

import pandas as pd
from datasets import load_dataset
from sklearn.model_selection import train_test_split

DATASET_ID = "gokulan006/risk-analysis-dataset"
os.makedirs("data", exist_ok=True)

# The dataset's `status` column uses a DIFFERENT order than train.py:
#   dataset: 0 = High Risk, 1 = Low Risk, 2 = Moderate Risk
#   ours:    0 = No Signal / Low, 1 = Mild / Moderate, 2 = High Risk
REMAP = {1: 0, 2: 1, 0: 2}
NAMES = {0: "No Signal (low)", 1: "Mild Risk (moderate)", 2: "High Risk"}


def clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    # keep Devanagari (U+0900-U+097F): Hindi vowel signs aren't "\w" and would be stripped
    text = re.sub(r"[^\w\s\u0900-\u097F.,!?'\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main():
    print(f"Downloading {DATASET_ID} ...")
    ds = load_dataset(DATASET_ID)
    print(ds)

    # Combine every split the dataset has (currently just 'train')
    df = pd.concat([ds[split].to_pandas() for split in ds], ignore_index=True)

    if "statement" not in df.columns or "status" not in df.columns:
        raise SystemExit(f"Unexpected columns {list(df.columns)} — the dataset may have changed.")

    df = df.dropna(subset=["statement", "status"])
    df["status"] = df["status"].astype(int)
    unknown = set(df["status"].unique()) - set(REMAP)
    if unknown:
        raise SystemExit(f"Unexpected label values {unknown} — the dataset may have changed.")

    df = pd.DataFrame({
        "text": df["statement"].astype(str).map(clean),
        "label": df["status"].map(REMAP),
    })
    df = df[df["text"].str.split().str.len() >= 5]   # skip very short posts
    df = df.drop_duplicates(subset="text").reset_index(drop=True)

    # Stratified 80 / 10 / 10 split so every split has the same class balance
    train, rest = train_test_split(df, test_size=0.2, stratify=df["label"], random_state=42)
    val, test = train_test_split(rest, test_size=0.5, stratify=rest["label"], random_state=42)

    train.to_csv("data/train.csv", index=False)
    val.to_csv("data/val.csv", index=False)
    test.to_csv("data/test.csv", index=False)

    print("\n✓ Saved:")
    print(f"  Train: {len(train)} rows")
    print(f"  Val:   {len(val)} rows")
    print(f"  Test:  {len(test)} rows")
    print("\n  Label distribution (train):")
    for label, count in train["label"].value_counts().sort_index().items():
        print(f"    {label} = {NAMES[label]:<22} {count}")

    print("\n  Example of each label (check these make sense!):")
    for label in sorted(NAMES):
        sample = train[train["label"] == label]["text"].iloc[0]
        print(f"    [{NAMES[label]}] {sample[:110]}...")

    print("\nNext → run: python train.py   (use Google Colab with a T4 GPU)")


if __name__ == "__main__":
    main()
