# ─────────────────────────────────────────────────────────────
# Step 1b — Add Hindi + Hinglish training data   (run on Colab GPU)
# Run AFTER prepare_data.py:   python prepare_multilingual.py
# Time: ~10-20 min on a T4 (translation is the slow part)
#
# What it does
#   1. Takes a stratified sample of the English posts from data/*.csv
#   2. Machine-translates them to Hindi (Helsinki-NLP/opus-mt-en-hi)
#   3. Makes a Hinglish version: Hindi romanised the way people type it
#      ("main bahut pareshaan hoon"), with some sentences left in English
#      so it looks like real code-mixed chat
#   4. Writes data_ml/{train,val,test}.csv with a `lang` column (en/hi/hinglish)
#
# Translations are cached in data_ml/translations.json, so if Colab
# disconnects you can just run it again and it continues.
#
# Honest limitation: Hindi/Hinglish examples are machine-translated, so the
# Hindi/Hinglish test scores measure translated text, not native posts.
# ─────────────────────────────────────────────────────────────

import json
import os
import random
import re

import pandas as pd

try:
    from src.hinglish import to_hinglish
except ImportError:          # on Colab, hinglish.py may sit next to this script
    from hinglish import to_hinglish

N_TRAIN = int(os.getenv("N_TRAIN", "6000"))   # posts translated for training
N_VAL = int(os.getenv("N_VAL", "600"))
N_TEST = int(os.getenv("N_TEST", "1000"))     # per language
MAX_SENTS = 4                                  # first N sentences of a post
KEEP_ENGLISH_P = float(os.getenv("KEEP_ENGLISH_P", "0.35"))  # code-mixing in Hinglish
MT_MODEL = os.getenv("MT_MODEL", "Helsinki-NLP/opus-mt-en-hi")
BATCH = int(os.getenv("MT_BATCH", "64"))
SEED = 42
OUT = "data_ml"
CACHE = os.path.join(OUT, "translations.json")


def clean(text: str) -> str:
    """Same as prepare_data.py / src/risk_model.py (keeps Devanagari)."""
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"[^\w\sऀ-ॿ.,!?'\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", str(text)) if p.strip()]
    return [p[:300] for p in parts[:MAX_SENTS]] or [str(text)[:300]]


def stratified_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    n = min(n, len(df))
    return (df.groupby("label", group_keys=False)
              .apply(lambda g: g.sample(max(1, round(n * len(g) / len(df))), random_state=SEED))
              .reset_index(drop=True))


class Translator:
    def __init__(self):
        import torch
        from transformers import MarianMTModel, MarianTokenizer

        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cpu":
            print("WARNING: no GPU — translation will be very slow. Use a Colab T4.", flush=True)
        self.tok = MarianTokenizer.from_pretrained(MT_MODEL)
        self.model = MarianMTModel.from_pretrained(MT_MODEL).to(self.device).eval()
        if self.device == "cuda":
            self.model = self.model.half()

    def __call__(self, batch: list[str]) -> list[str]:
        enc = self.tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=128).to(self.device)
        with self.torch.no_grad():
            out = self.model.generate(**enc, max_new_tokens=160, num_beams=1)
        return self.tok.batch_decode(out, skip_special_tokens=True)


def translate_all(sents: list[str], translate=None) -> dict:
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            cache = json.load(f)
        print(f"Loaded {len(cache)} cached translations", flush=True)
    todo = sorted({s for s in sents if s not in cache}, key=len)  # similar lengths batch faster
    if todo:
        translate = translate or Translator()
        print(f"Translating {len(todo)} sentences to Hindi ...", flush=True)
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            for src, hi in zip(batch, translate(batch)):
                cache[src] = hi
            if (i // BATCH) % 20 == 0 or i + BATCH >= len(todo):
                with open(CACHE, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False)
                print(f"  {min(i + BATCH, len(todo))}/{len(todo)}", flush=True)
    return cache


def build_rows(df: pd.DataFrame, cache: dict, rng: random.Random) -> list[dict]:
    rows = []
    for text, label in zip(df["text"], df["label"]):
        en_sents = sentences(text)
        hi_sents = [cache[s] for s in en_sents]
        hindi = clean(" ".join(hi_sents))
        mixed = [s if rng.random() < KEEP_ENGLISH_P else to_hinglish(h) for s, h in zip(en_sents, hi_sents)]
        if all(m == s for m, s in zip(mixed, en_sents)):   # make sure some Hindi is in there
            mixed[0] = to_hinglish(hi_sents[0])
        hinglish = clean(" ".join(mixed))
        if len(hindi.split()) >= 3:
            rows.append({"text": hindi, "label": int(label), "lang": "hi"})
        if len(hinglish.split()) >= 3:
            rows.append({"text": hinglish, "label": int(label), "lang": "hinglish"})
    return rows


def main(translate=None):
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(SEED)
    splits = {name: pd.read_csv(f"data/{name}.csv") for name in ("train", "val", "test")}
    samples = {
        "train": stratified_sample(splits["train"], N_TRAIN),
        "val": stratified_sample(splits["val"], N_VAL),
        "test": stratified_sample(splits["test"], N_TEST),
    }
    all_sents = [s for df in samples.values() for t in df["text"] for s in sentences(t)]
    cache = translate_all(all_sents, translate)

    for name, df_en in splits.items():
        en = df_en.assign(lang="en")[["text", "label", "lang"]]
        extra = pd.DataFrame(build_rows(samples[name], cache, rng))
        out = pd.concat([en, extra], ignore_index=True)
        if name == "train":
            out = out.sample(frac=1, random_state=SEED).reset_index(drop=True)
        out.to_csv(f"{OUT}/{name}.csv", index=False)
        print(f"\n{name}: {len(out)} rows", flush=True)
        print(out.groupby(["lang", "label"]).size().unstack(fill_value=0).to_string(), flush=True)

    ex = pd.read_csv(f"{OUT}/train.csv")
    print("\nExamples (check they make sense!):")
    for lang in ("hi", "hinglish"):
        for label in (0, 1, 2):
            row = ex[(ex["lang"] == lang) & (ex["label"] == label)].head(1)
            if len(row):
                print(f"  [{lang} | label {label}] {row['text'].iloc[0][:110]}")
    print("\nNext → run: DATA_DIR=data_ml MODEL_NAME=google/muril-base-cased python train.py")


if __name__ == "__main__":
    main()
