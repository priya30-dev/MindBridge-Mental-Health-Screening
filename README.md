# MindBridge – AI-Powered Mental Health Screening System

## Overview

MindBridge is an AI-powered mental health screening platform designed to detect emotional distress signals from text and audio inputs. The system combines Natural Language Processing (NLP), audio analysis, explainable AI, and risk assessment techniques to provide an early screening tool for identifying potential mental health concerns.

The platform is intended for educational and research purposes and does not replace professional medical diagnosis.

---

## Features

### Text Analysis

* Emotion detection using a fine-tuned RoBERTa model
* Confidence scoring for predictions
* Explainable AI using SHAP
* Word-level contribution analysis

### Audio Analysis

* Audio feature extraction
* Speech emotion analysis
* Risk signal identification from voice patterns

### Risk Assessment

* Dynamic risk scoring (0–100)
* Risk level classification:

  * LOW
  * MEDIUM
  * HIGH
  * CRITICAL
* Automated alert flags

### Risk Model Results

Fine-tuned `roberta-base` (3 epochs, mixed precision, Colab T4) to classify posts as **No Signal / Mild Risk / High Risk**.
Test set: 4,350 held-out posts.

| Class | Precision | Recall | F1 |
|---|---|---|---|
| No Signal | 0.965 | 0.946 | 0.955 |
| Mild Risk | 0.830 | 0.833 | 0.831 |
| High Risk | 0.751 | 0.764 | 0.757 |
| **Weighted avg** | **0.851** | **0.849** | **0.850** |

Confusion matrix (rows = true, columns = predicted):

| | No Signal | Mild | High |
|---|---|---|---|
| **No Signal** | 1273 | 55 | 18 |
| **Mild** | 34 | 1539 | 275 |
| **High** | 12 | 261 | 883 |

**Safety view:** 99% of High Risk posts (1,144 of 1,156) are flagged as at least Mild Risk; only 12 are missed entirely. The rule-based safety net below adds a second layer for explicit crisis language.

Reproduce: `python prepare_data.py` then `python train.py` (GPU recommended). Dataset: [gokulan006/risk-analysis-dataset](https://huggingface.co/datasets/gokulan006/risk-analysis-dataset), built from the Kaggle datasets "Sentiment Analysis for Mental Health" and "Suicidal Tweet Detection" — see their licenses.

### Hindi + Hinglish (multilingual model)

`prepare_multilingual.py` adds Hindi and Hinglish versions of ~6,000 training posts: machine-translated
with `Helsinki-NLP/opus-mt-en-hi`, then romanised the way people type Hinglish ("main bahut pareshaan hoon"),
with some sentences left in English for realistic code-mixing (`src/hinglish.py`).
`train.py` then fine-tunes `google/muril-base-cased` (trained on 17 Indian languages and their romanised forms)
and reports scores separately for English, Hindi and Hinglish.

```bash
python prepare_data.py
python prepare_multilingual.py                      # GPU recommended
DATA_DIR=data_ml MODEL_NAME=google/muril-base-cased python train.py
python benchmark_model.py                           # fp32 vs int8 speed + accuracy on your machine
```

Limitation: Hindi/Hinglish examples are machine-translated, so their scores measure translated text, not native posts.

**Results** (same held-out test posts for every model; Hindi/Hinglish = 998 machine-translated posts each):

| Test set | English model (RoBERTa) | Multilingual model (MuRIL) |
|---|---|---|
| English — weighted F1 | **0.850** | 0.825 |
| English — High Risk recall | **76.4%** | 70.8% |
| English — High Risk flagged ≥ Mild | **99.0%** | 98.3% |
| Hindi — weighted F1 | – | **0.734** |
| Hindi — High Risk flagged ≥ Mild | – | **93.6%** |
| Hinglish — weighted F1 | – | **0.745** |
| Hinglish — High Risk flagged ≥ Mild | – | **94.4%** |

**Language-aware routing:** the multilingual model costs ~2.5 F1 points on English, so the app keeps both.
Each check-in's language is detected (Devanagari → Hindi; common romanised-Hindi words → Hinglish;
otherwise English) and sent to the stronger model for it: English → RoBERTa (`./model_english`),
Hindi/Hinglish → MuRIL (`./model`). Set `LANGUAGE_ROUTING=0` to use one model for everything.

### Speed

On CPU the risk model is quantized to int8 automatically (`RISK_QUANTIZE=auto`), and the word-level explanation
is capped (`SHAP_MAX_EVALS=80`). `benchmark_model.py` measures the speed-up and any accuracy change on your machine.

### Safety Layer

* Rule-based crisis-language detection (`src/safety.py`) runs on every request, independent of the ML model
* Explicit self-harm / suicidal language always raises the score to CRITICAL
* Helplines (Tele-MANAS 14416, iCall, 112) are returned by the API and shown first in the dashboard
* Offline demo results are clearly labelled and never shown for audio
* Supports Hindi (Devanagari, with or without nukta) and common Hinglish crisis phrases

### Explainable AI

* SHAP-based interpretation
* Token-level importance visualization
* Transparent prediction reasoning

### Text + Voice Check-ins

* Type, record a voice note in the browser, or both — scored together (text 65%, voice 35%)
* "How you sounded" cues (energy, tone, pauses) compared with **your own** voice baseline, not a universal threshold
* Optional speech-to-text (faster-whisper) so voice-only check-ins also get text analysis and the safety check
* Words that pushed stress up or down are highlighted right inside your message (SHAP)
* "Does this feel right?" feedback saved for future model improvement
* Trend alerts when check-ins keep getting heavier

### Accounts, Journal & History

* Sign up / log in (JWT, PBKDF2-hashed passwords, login rate limiting)
* Every check-in saved to SQLite or PostgreSQL; private mode stores scores only, never words
* Mood journal with writing prompts, weekly stress bars, and the safety net on every entry

### Chill Zone (comfort tools)

* Breathing bubble (box breathing) with session tracking
* Soundscapes generated live in the browser (rain, ocean, campfire, brown/white noise) — no audio files
* Affirmations, a "let it go" worry release (worries are never stored), 5-4-3-2-1 grounding
* Personal comfort kit saved to your account

### Check-up Questionnaires

* PHQ-9 (depression) and GAD-7 (anxiety) with standard scoring bands
* PHQ-9 item 9 (self-harm thoughts) triggers the crisis support flow

### Wellness Report ("your month, wrapped")

* Check-ins, average stress vs previous period, calm minutes, best day
* Stress trend chart, mood mix, words that weighed on you, what helped
* Downloadable PDF report

### Support, Privacy & Counsellor View

* One-tap helplines (Tele-MANAS 14416, iCall, 112) and a ready-made message to a trusted contact
* Export all my data (JSON) and permanently delete my account
* Opt-in counsellor dashboard: pseudonymised high-stress check-ins with a review workflow — counsellors never see users' words or identity

### Backend API

* FastAPI REST API (`/docs` for interactive docs) with versioned routes under `/api/v1`
* Accounts, check-ins, journal, questionnaires, comfort, reports, privacy and counsellor routers
* 45 automated tests run in GitHub Actions on every push

---

## Tech Stack

### Machine Learning

* PyTorch
* Hugging Face Transformers
* RoBERTa
* SHAP

### Backend

* FastAPI
* Pydantic
* Uvicorn

### Frontend

* Streamlit
* Plotly

### Testing

* PyTest

### Utilities

* NumPy
* Pandas
* Scikit-learn

---

## Project Architecture

```text
MindBridge/
│
├── api/
│   ├── routers/
│   │   ├── text.py
│   │   └── audio.py
│   ├── schemas.py
│   └── main.py
│
├── dashboard/
│   └── app.py
│
├── src/
│   ├── text_model.py
│   ├── audio_model.py
│   ├── fusion.py
│   ├── explainer.py
│   ├── predict.py
│   └── utils.py
│
├── tests/
│   ├── test_text.py
│   ├── test_audio.py
│   └── test_api.py
│
├── requirements.txt
└── README.md
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/priya30-dev/MindBridge-Mental-Health-Screening.git

cd MindBridge-Mental-Health-Screening
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Backend

```bash
cp .env.example .env        # then set SECRET_KEY
uvicorn api.main:app --reload
```

The database is created automatically (SQLite at `./data/mindbridge.db` by default).
To get a counsellor account, add its email to `COUNSELLOR_EMAILS` in `.env` before signing up.

### Run everything with Docker

```bash
docker compose up --build   # API on :8000, dashboard on :8501, PostgreSQL included
```

Put the trained model weights in `./models/` first.

API Documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Running the Dashboard

```bash
streamlit run dashboard/app.py
```

---

## Testing

Run all tests:

```bash
pytest tests/ -v
```

Tests that don't need the trained weights (these run in CI):

```bash
pytest tests/test_safety.py tests/test_fusion.py tests/test_audio.py tests/test_platform.py -v
```

Tests include:

* Crisis-language detection (including false-positive checks like "great weekend")
* Risk fusion and level boundaries
* Accounts, login rate limiting, check-ins (text, voice, text + voice), private mode
* Journal, PHQ-9/GAD-7 scoring, reports and PDF, data export and deletion
* Counsellor access control and pseudonymisation
* Text/audio model validation (needs weights in `models/`)

---

## Key Components

### RoBERTa Text Model

Used for emotion classification and mental health signal detection from textual inputs.

### Audio Analysis Module

Processes speech features to identify emotional indicators present in voice recordings.

### SHAP Explainability

Provides transparency by highlighting the most influential words contributing to model predictions.

### Risk Fusion Engine

Combines signals from multiple modalities and generates:

* Risk Score
* Risk Level
* Alert Flags
* Recommendations

---

## Future Improvements

* Dedicated suicide/self-harm risk classifier with published precision/recall
* Hindi + Hinglish model (XLM-R / MuRIL)
* Transformer-based audio models
* ONNX export / quantisation for faster inference
* Clinical evaluation pipeline
* Public cloud deployment

---

## Disclaimer

MindBridge is an educational and research-oriented project. The results generated by this system should not be considered a medical diagnosis. Individuals experiencing mental health concerns should consult qualified healthcare professionals.

---

## Author

**Priya Singh**

B.Tech Computer Science Engineering
Jaypee Institute of Information Technology (JIIT)

GitHub: https://github.com/priya30-dev
