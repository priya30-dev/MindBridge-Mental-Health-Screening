import os
import librosa
import numpy as np
import pandas as pd

DATASET_PATH = "data/raw/ravdess"
OUTPUT_CSV = "data/audio_features.csv"

rows = []

for root, dirs, files in os.walk(DATASET_PATH):
    for file in files:
        if file.endswith(".wav"):
            path = os.path.join(root, file)

            y, sr = librosa.load(path, sr=22050)

            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)

            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_std = np.std(mfcc, axis=1)

            delta = librosa.feature.delta(mfcc)
            delta_mean = np.mean(delta, axis=1)

            zcr = np.mean(librosa.feature.zero_crossing_rate(y))
            rms = np.mean(librosa.feature.rms(y=y))

            features = np.concatenate([
                mfcc_mean,
                mfcc_std,
                delta_mean,
                [zcr, rms]
            ])

            emotion = int(file.split("-")[2])

            # 1 = high emotional risk, 0 = low emotional risk
            label = 1 if emotion in [4, 5, 6] else 0

            row = list(features)
            row.append(label)
            rows.append(row)

columns = [f"f{i}" for i in range(122)]
columns.append("label")

df = pd.DataFrame(rows, columns=columns)
df.to_csv(OUTPUT_CSV, index=False)

print("Saved:", OUTPUT_CSV)
print("Samples:", len(df))