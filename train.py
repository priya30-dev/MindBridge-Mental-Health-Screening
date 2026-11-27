# ─────────────────────────────────────────────────────────────
# Step 2 of 4 — Fine-tune RoBERTa
# Run: python train.py
# Time: ~20-25 mins on Colab T4 GPU (mixed precision) | hours on CPU (use Colab!)
#
# On Colab, run it in the background so an interrupted cell can't stop it:
#   !nohup python -u train.py > train.log 2>&1 &
#   !tail -c 400 train.log        # check progress any time
#
# HOW TO RUN ON GOOGLE COLAB (free GPU):
# 1. Upload this whole folder to Colab
# 2. Runtime → Change runtime type → T4 GPU
# 3. !pip install -r requirements.txt
# 4. !python prepare_data.py
# 5. !python train.py
# ─────────────────────────────────────────────────────────────

import os, torch
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.metrics import f1_score, classification_report
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────
# English only (default):        python train.py
# English + Hindi + Hinglish:    DATA_DIR=data_ml MODEL_NAME=google/muril-base-cased python train.py
MODEL_NAME  = os.getenv("MODEL_NAME", "roberta-base")
DATA_DIR    = os.getenv("DATA_DIR", "data")
NUM_LABELS  = 3
MAX_LEN     = 128       # shorter = faster, still works well
BATCH_SIZE  = 16        # reduce to 8 if GPU OOM
EPOCHS      = 3         # 3 is enough for fine-tuning
LR          = float(os.getenv("LR", "2e-5"))
SAVE_DIR    = "./model"
DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")
USE_AMP     = DEVICE.type == "cuda"   # mixed precision: ~2x faster on T4

print(f"Device: {DEVICE}  |  mixed precision: {USE_AMP}  |  model: {MODEL_NAME}  |  data: {DATA_DIR}", flush=True)
LABEL_NAMES = ["No Signal", "Mild Risk", "High Risk"]
os.makedirs(SAVE_DIR, exist_ok=True)


# ── Dataset ───────────────────────────────────────────────────
class MHDataset(Dataset):
    def __init__(self, path, tokenizer):
        self.df  = pd.read_csv(path)
        self.tok = tokenizer

    def __len__(self):
        return len(self.df)

    def __getitem__(self, i):
        row = self.df.iloc[i]
        enc = self.tok(
            str(row["text"]),
            max_length=MAX_LEN,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids":      enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels":         torch.tensor(int(row["label"]), dtype=torch.long),
        }


# ── Train ─────────────────────────────────────────────────────
def train():
    tok   = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
                MODEL_NAME, num_labels=NUM_LABELS).to(DEVICE)

    train_loader = DataLoader(MHDataset(f"{DATA_DIR}/train.csv", tok),
                              batch_size=BATCH_SIZE, shuffle=True,  num_workers=2)
    val_loader   = DataLoader(MHDataset(f"{DATA_DIR}/val.csv",   tok),
                              batch_size=BATCH_SIZE, shuffle=False, num_workers=2)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    total     = len(train_loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(
                    optimizer,
                    num_warmup_steps=total // 10,
                    num_training_steps=total)

    try:
        scaler = torch.amp.GradScaler("cuda", enabled=USE_AMP)
    except (AttributeError, TypeError):   # older torch
        scaler = torch.cuda.amp.GradScaler(enabled=USE_AMP)
    best_f1 = 0.0

    for epoch in range(EPOCHS):
        # ── Training loop ──────────────────────────────────────
        model.train()
        total_loss = 0
        for batch in tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS} train", mininterval=20):
            ids  = batch["input_ids"].to(DEVICE)
            mask = batch["attention_mask"].to(DEVICE)
            labs = batch["labels"].to(DEVICE)

            with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USE_AMP):
                out  = model(input_ids=ids, attention_mask=mask, labels=labs)
                loss = out.loss
            total_loss += loss.item()

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            optimizer.zero_grad()

        avg_loss = total_loss / len(train_loader)

        # ── Validation loop ────────────────────────────────────
        model.eval()
        preds, truths = [], []
        with torch.no_grad():
            for batch in tqdm(val_loader, desc=f"Epoch {epoch+1}/{EPOCHS} val", mininterval=20):
                ids  = batch["input_ids"].to(DEVICE)
                mask = batch["attention_mask"].to(DEVICE)
                with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USE_AMP):
                    out = model(input_ids=ids, attention_mask=mask)
                pred = out.logits.argmax(dim=-1).cpu().numpy()
                preds.extend(pred)
                truths.extend(batch["labels"].numpy())

        f1 = f1_score(truths, preds, average="weighted")
        print(f"\n  Epoch {epoch+1} done  |  Loss: {avg_loss:.4f}  |  Weighted F1: {f1:.4f}", flush=True)

        if f1 > best_f1:
            best_f1 = f1
            model.save_pretrained(SAVE_DIR)
            tok.save_pretrained(SAVE_DIR)
            print(f"  ✓ Model saved  (best F1 so far: {best_f1:.4f})", flush=True)

    # ── Final test evaluation ──────────────────────────────────
    print("\n── Final evaluation on test set ──")
    # Reload the BEST checkpoint (saved above) so the reported metrics match the saved model
    model = AutoModelForSequenceClassification.from_pretrained(SAVE_DIR).to(DEVICE)
    model.eval()
    test_ds     = MHDataset(f"{DATA_DIR}/test.csv", tok)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)
    preds, truths = [], []
    with torch.no_grad():
        for batch in tqdm(test_loader, desc="Test", mininterval=20):
            ids  = batch["input_ids"].to(DEVICE)
            mask = batch["attention_mask"].to(DEVICE)
            with torch.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=USE_AMP):
                out = model(input_ids=ids, attention_mask=mask)
            preds.extend(out.logits.argmax(dim=-1).cpu().numpy())
            truths.extend(batch["labels"].numpy())

    from sklearn.metrics import confusion_matrix

    truths, preds = np.array(truths), np.array(preds)

    def section(title, t, p):
        cm = confusion_matrix(t, p, labels=[0, 1, 2])
        high = cm[2].sum()
        flagged = (cm[2, 1] + cm[2, 2]) / high if high else float("nan")
        return (f"\n=== {title} ({len(t)} posts) ===\n"
                f"Weighted F1: {f1_score(t, p, average='weighted'):.4f}\n"
                + classification_report(t, p, digits=4, labels=[0, 1, 2], target_names=LABEL_NAMES, zero_division=0)
                + "Confusion matrix (rows = true, cols = predicted; No Signal, Mild, High):\n"
                + str(cm) + "\n"
                + f"High Risk posts flagged as at least Mild: {flagged:.1%}\n")

    report = section("ALL", truths, preds)
    langs = sorted(test_ds.df["lang"].unique()) if "lang" in test_ds.df.columns else ["en"]
    if "lang" in test_ds.df.columns:
        lang_col = test_ds.df["lang"].to_numpy()
        names = {"en": "English", "hi": "Hindi (machine-translated)", "hinglish": "Hinglish (machine-translated + romanised)"}
        for lang in langs:
            m = lang_col == lang
            report += section(names.get(lang, lang), truths[m], preds[m])
    print(report, flush=True)

    # Save metrics + model info (the app reads model_info.json)
    final_f1 = f1_score(truths, preds, average="weighted")
    with open(os.path.join(SAVE_DIR, "metrics.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    import json
    with open(os.path.join(SAVE_DIR, "model_info.json"), "w", encoding="utf-8") as f:
        json.dump({"base_model": MODEL_NAME, "languages": [str(l) for l in langs],
                   "labels": LABEL_NAMES, "max_len": MAX_LEN, "test_weighted_f1": round(final_f1, 4)}, f, indent=2)

    print(f"\n✓ Training complete. F1: {final_f1:.4f}", flush=True)
    print(f"  Metrics saved to {SAVE_DIR}/metrics.txt")


if __name__ == "__main__":
    train()
