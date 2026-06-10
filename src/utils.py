import librosa
import numpy as np
import re
import os
import pandas as pd
from datasets import load_from_disk

def clean_text(text: str) -> str:
    """Basic text normalisation."""
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"[^\w\s.,!?'\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def prepare_reddit_dataset(save_dir: str = "./data/processed"):
    os.makedirs(save_dir, exist_ok=True)

    ds = load_from_disk("./data/raw/reddit")
    rows = []

    for split in ["train", "validation", "test"]:
        for item in ds[split]:
            rows.append({
                "text": clean_text(item["text"]),
                "label": int(item["label"]),
                "split": split,
            })

    df = pd.DataFrame(rows)

    df = df[df["text"].str.split().str.len() >= 5]
    df = df.drop_duplicates(subset="text")

    train_df = df[df["split"] == "train"].drop(columns="split")
    val_df = df[df["split"] == "validation"].drop(columns="split")
    test_df = df[df["split"] == "test"].drop(columns="split")

    train_df.to_csv(f"{save_dir}/text_train.csv", index=False)
    val_df.to_csv(f"{save_dir}/text_val.csv", index=False)
    test_df.to_csv(f"{save_dir}/text_test.csv", index=False)

    print(f"Train: {len(train_df)} Val: {len(val_df)} Test: {len(test_df)}")

if __name__ == "__main__":
    prepare_reddit_dataset()
    import librosa
import numpy as np

def extract_audio_features(filepath: str, sr: int = 16000, n_mfcc: int = 40) -> np.ndarray:
    """
    Returns a 1-D feature vector of length 122.
    MFCC mean + MFCC std + delta mean + ZCR + pitch.
    """
    y, _ = librosa.load(filepath, sr=sr, mono=True)

    y, _ = librosa.effects.trim(y, top_db=20)

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)

    mfcc_mean = mfcc.mean(axis=1)
    mfcc_std = mfcc.std(axis=1)

    delta = librosa.feature.delta(mfcc)
    delta_mean = delta.mean(axis=1)

    zcr_mean = librosa.feature.zero_crossing_rate(y).mean()

    f0, _, _ = librosa.pyin(y, fmin=75, fmax=300, sr=sr)
    pitch_mean = np.nanmean(f0) if f0 is not None else 0.0

    features = np.concatenate([
        mfcc_mean,
        mfcc_std,
        delta_mean,
        [zcr_mean, pitch_mean]
    ])

    return features.astype(np.float32)


def build_audio_feature_csv(
    daic_root: str,
    save_path: str = "./data/processed/audio_features.csv"
):
    import os
    import glob
    import pandas as pd

    records = []

    for wav_path in glob.glob(f"{daic_root}/**/*.wav", recursive=True):
        participant_id = os.path.basename(os.path.dirname(wav_path))

        try:
            feats = extract_audio_features(wav_path)

            label_file = os.path.join(daic_root, participant_id, "label.txt")
            label = int(open(label_file).read().strip())

            row = {
                "participant": participant_id,
                "label": label
            }

            for i, v in enumerate(feats):
                row[f"f{i}"] = v

            records.append(row)

        except Exception as e:
            print(f"Skipping {wav_path}: {e}")

    pd.DataFrame(records).to_csv(save_path, index=False)
    print(f"Saved {len(records)} rows to {save_path}")