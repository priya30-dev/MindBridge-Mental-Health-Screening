# ─────────────────────────────────────────────────────────────
# Speed check: normal (fp32) vs quantized (int8) risk model on THIS computer
# Run:  python benchmark_model.py            (uses data_ml/test.csv or data/test.csv)
#       python benchmark_model.py --n 300    (how many test posts to score)
#
# Prints latency per check-in, accuracy (weighted F1) for both versions,
# and how often they agree. Saves the table to model/benchmark.txt
# ─────────────────────────────────────────────────────────────

import argparse
import os
import time

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from src.risk_model import RISK_MODEL_DIR, _probs, load_risk_model, model_info


def run(tok, model, texts, labels, n_latency):
    # warm-up so we don't time one-off setup
    _probs(texts[:2], tok, model)
    t0 = time.perf_counter()
    for t in texts[:n_latency]:
        _probs([t], tok, model)               # one check-in at a time, like the app
    latency_ms = (time.perf_counter() - t0) / n_latency * 1000

    preds = []
    for i in range(0, len(texts), 32):
        preds.extend(_probs(texts[i:i + 32], tok, model).argmax(axis=1))
    preds = np.array(preds)
    return latency_ms, preds, f1_score(labels, preds, average="weighted")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="test posts to score")
    ap.add_argument("--latency-n", type=int, default=40, help="posts to time one by one")
    args = ap.parse_args()

    path = "data_ml/test.csv" if os.path.exists("data_ml/test.csv") else "data/test.csv"
    df = pd.read_csv(path)
    df = df.groupby("lang", group_keys=False).apply(lambda g: g.sample(min(len(g), args.n // df["lang"].nunique()), random_state=0)) \
        if "lang" in df.columns else df.sample(min(len(df), args.n), random_state=0)
    texts, labels = df["text"].astype(str).tolist(), df["label"].to_numpy()
    n_lat = min(args.latency_n, len(texts))
    print(f"Model: {model_info().get('base_model')}  |  test file: {path}  |  {len(texts)} posts\n", flush=True)

    results = {}
    for name, q in (("normal (fp32)", False), ("quantized (int8)", True)):
        tok, model = load_risk_model(RISK_MODEL_DIR, quantized=q)
        results[name] = run(tok, model, texts, labels, n_lat)
        print(f"  {name:<17} {results[name][0]:7.1f} ms per check-in   weighted F1 {results[name][2]:.4f}", flush=True)

    (lat32, p32, f32), (lat8, p8, f8) = results.values()
    lines = [
        f"Benchmark on this computer ({len(texts)} test posts from {path})",
        f"{'version':<18}{'ms / check-in':>15}{'weighted F1':>14}",
        f"{'normal (fp32)':<18}{lat32:>15.1f}{f32:>14.4f}",
        f"{'quantized (int8)':<18}{lat8:>15.1f}{f8:>14.4f}",
        f"Speed-up: {lat32 / lat8:.2f}x   |   F1 change: {f8 - f32:+.4f}   |   same prediction: {(p32 == p8).mean():.1%}",
    ]
    if "lang" in df.columns:
        for lang in sorted(df["lang"].unique()):
            m = (df["lang"] == lang).to_numpy()
            lines.append(f"  {lang:<9} F1 fp32 {f1_score(labels[m], p32[m], average='weighted'):.4f}"
                         f"  int8 {f1_score(labels[m], p8[m], average='weighted'):.4f}")
    report = "\n".join(lines)
    print("\n" + report)
    with open(os.path.join(RISK_MODEL_DIR, "benchmark.txt"), "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\nSaved to {RISK_MODEL_DIR}/benchmark.txt")


if __name__ == "__main__":
    main()
