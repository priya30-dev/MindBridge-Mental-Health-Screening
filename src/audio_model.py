import os
from dotenv import load_dotenv

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import joblib

from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, accuracy_score
from tqdm import tqdm


load_dotenv()

AUDIO_FEATURES = 122
BATCH_SIZE = 32
EPOCHS = 30
LR = 1e-3

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MODEL_SAVE_PATH = os.getenv("AUDIO_MODEL_PATH", "./models/audio_cnn.pt")
SCALER_PATH = os.getenv("AUDIO_SCALER_PATH", "./models/audio_scaler.pkl")
CSV_PATH = "./data/audio_features.csv"


class AudioFeatDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, index):
        return self.X[index], self.y[index]


class AudioCNN(nn.Module):
    def __init__(self, n_features: int = AUDIO_FEATURES, n_classes: int = 2):
        super().__init__()

        self.conv = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(16),
        )

        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 16, 128),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.conv(x)
        return self.fc(x)


def train_audio_model(csv_path: str = CSV_PATH):
    os.makedirs("./models", exist_ok=True)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError("audio_features.csv is empty. Run extract_audio_features.py first.")

    if "label" not in df.columns:
        raise ValueError("CSV must contain a 'label' column.")

    feature_cols = [col for col in df.columns if col.startswith("f")]

    if len(feature_cols) != AUDIO_FEATURES:
        raise ValueError(f"Expected 122 feature columns, found {len(feature_cols)}")

    X = df[feature_cols].values.astype(np.float32)
    y = df["label"].values.astype(np.int64)

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    joblib.dump(scaler, SCALER_PATH)

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    train_loader = DataLoader(
        AudioFeatDataset(X_train, y_train),
        batch_size=BATCH_SIZE,
        shuffle=True,
    )

    val_loader = DataLoader(
        AudioFeatDataset(X_val, y_val),
        batch_size=BATCH_SIZE,
        shuffle=False,
    )

    n_classes = len(np.unique(y))

    model = AudioCNN(n_classes=n_classes).to(DEVICE)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    best_f1 = 0.0

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0

        for X_batch, y_batch in tqdm(train_loader, desc=f"Epoch {epoch + 1}/{EPOCHS}"):
            X_batch = X_batch.to(DEVICE)
            y_batch = y_batch.to(DEVICE)

            optimizer.zero_grad()

            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)

            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        model.eval()
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch = X_batch.to(DEVICE)

                outputs = model(X_batch)
                preds = torch.argmax(outputs, dim=1).cpu().numpy()

                all_preds.extend(preds)
                all_labels.extend(y_batch.numpy())

        val_acc = accuracy_score(all_labels, all_preds)
        val_f1 = f1_score(all_labels, all_preds, average="weighted")

        print(
            f"Epoch {epoch + 1}/{EPOCHS} | "
            f"Loss: {total_loss / len(train_loader):.4f} | "
            f"Val Acc: {val_acc:.4f} | "
            f"Val F1: {val_f1:.4f}"
        )

        if val_f1 > best_f1:
            best_f1 = val_f1
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print("Best audio model saved.")

    print("Training completed.")
    print("Best F1:", best_f1)


def load_audio_model(n_classes: int = 2):
    model = AudioCNN(n_classes=n_classes).to(DEVICE)

    model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=DEVICE))
    model.eval()

    scaler = joblib.load(SCALER_PATH)

    return model, scaler


def predict_audio_features(features: np.ndarray, model, scaler):
    if features.ndim == 1:
        features = features.reshape(1, -1)

    features = scaler.transform(features)

    X = torch.tensor(features, dtype=torch.float32).to(DEVICE)

    with torch.no_grad():
        logits = model(X)
        probs = torch.softmax(logits, dim=1)
        preds = torch.argmax(probs, dim=1)

    return {
        "label": int(preds.cpu().numpy()[0]),
        "probabilities": probs.cpu().numpy()[0].tolist(),
        "risk_score": round(float(probs.cpu().numpy()[0][1]) * 100, 2),
    }


if __name__ == "__main__":
    train_audio_model()