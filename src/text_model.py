from dotenv import load_dotenv
import os

load_dotenv()

SAVE_PATH = os.getenv(
    "TEXT_MODEL_PATH",
    "./models/roberta_finetuned"
)

import os
import torch
import numpy as np
import pandas as pd

from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)

from sklearn.metrics import f1_score
from tqdm import tqdm

MODEL_NAME = "distilroberta-base"
NUM_LABELS = 6
MAX_LEN = 128
BATCH_SIZE = 4
EPOCHS = 1
LR = 2e-5

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SAVE_PATH = "./models/roberta_finetuned"

print(f"Using device: {DEVICE}")


class MentalHealthDataset(Dataset):
    def __init__(self, csv_path: str, tokenizer, max_len: int = MAX_LEN):
        self.df = pd.read_csv(csv_path)
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]

        text = str(row["text"])
        label = int(row["label"])

        encoding = self.tokenizer(
            text,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(label, dtype=torch.long),
        }


def create_small_train_file():
    input_path = "./data/processed/text_train.csv"
    output_path = "./data/processed/text_train_small.csv"

    if not os.path.exists(output_path):
        df = pd.read_csv(input_path)
        df = df.sample(min(2000, len(df)), random_state=42)
        df.to_csv(output_path, index=False)
        print("Created small training file:", output_path)


def train_text_model():
    create_small_train_file()

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS
    ).to(DEVICE)

    train_loader = DataLoader(
        MentalHealthDataset("./data/processed/text_train_small.csv", tokenizer),
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0
    )

    val_loader = DataLoader(
        MentalHealthDataset("./data/processed/text_val.csv", tokenizer),
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)

    total_steps = len(train_loader) * EPOCHS

    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, total_steps // 10),
        num_training_steps=total_steps
    )

    best_f1 = 0.0

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0

        for batch in tqdm(train_loader, desc=f"Epoch {epoch + 1}/{EPOCHS} [train]"):
            ids = batch["input_ids"].to(DEVICE)
            mask = batch["attention_mask"].to(DEVICE)
            labs = batch["labels"].to(DEVICE)

            outputs = model(input_ids=ids, attention_mask=mask, labels=labs)
            loss = outputs.loss

            total_loss += loss.item()

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

        avg_loss = total_loss / len(train_loader)

        model.eval()
        all_preds = []
        all_labels = []

        with torch.no_grad():
            for batch in tqdm(val_loader, desc=f"Epoch {epoch + 1}/{EPOCHS} [val]"):
                ids = batch["input_ids"].to(DEVICE)
                mask = batch["attention_mask"].to(DEVICE)
                labs = batch["labels"].cpu().numpy()

                logits = model(input_ids=ids, attention_mask=mask).logits
                preds = logits.argmax(dim=-1).cpu().numpy()

                all_preds.extend(preds)
                all_labels.extend(labs)

        f1 = f1_score(all_labels, all_preds, average="weighted")

        print(f"Loss: {avg_loss:.4f} Weighted F1: {f1:.4f}")

        if f1 > best_f1:
            best_f1 = f1

            os.makedirs(SAVE_PATH, exist_ok=True)
            model.save_pretrained(SAVE_PATH)
            tokenizer.save_pretrained(SAVE_PATH)

            print(f"Model saved. Best F1: {best_f1:.4f}")

    print("Training complete.")


def load_text_model(path: str = SAVE_PATH):
    tokenizer = AutoTokenizer.from_pretrained(path)

    model = AutoModelForSequenceClassification.from_pretrained(path).to(DEVICE)

    model.eval()

    return tokenizer, model


def predict_text(text: str, tokenizer, model):
    encoding = tokenizer(
        text,
        max_length=MAX_LEN,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    ids = encoding["input_ids"].to(DEVICE)
    mask = encoding["attention_mask"].to(DEVICE)

    with torch.no_grad():
        logits = model(input_ids=ids, attention_mask=mask).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

    label = int(np.argmax(probs))

    emotion_labels = {
        0: "sadness",
        1: "joy",
        2: "love",
        3: "anger",
        4: "fear",
        5: "surprise"
    }

    return {
        "label": label,
        "emotion": emotion_labels.get(label, "unknown"),
        "probabilities": probs.tolist(),
        "confidence": round(float(max(probs) * 100), 2)
    }


if __name__ == "__main__":
    train_text_model()