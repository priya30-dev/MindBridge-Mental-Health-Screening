import os
import sys
import json

# Make src imports work when running: python src/predict.py
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from text_model import load_text_model, predict_text
from audio_model import load_audio_model, predict_audio_features
from fusion import fuse_scores
from explainer import explain_text
from utils import extract_audio_features


def emotion_to_risk(text_result: dict) -> float:
    emotion = text_result["emotion"]
    confidence = text_result["confidence"]

    risk_weights = {
        "sadness": 0.85,
        "fear": 0.75,
        "anger": 0.65,
        "surprise": 0.35,
        "love": 0.15,
        "joy": 0.05,
    }

    weight = risk_weights.get(emotion, 0.5)
    return round(confidence * weight, 2)


def run_prediction(text: str, audio_path: str | None = None):
    tokenizer, text_model = load_text_model()

    text_result = predict_text(text, tokenizer, text_model)
    text_score = emotion_to_risk(text_result)

    audio_result = None
    audio_score = None

    if audio_path is not None and os.path.exists(audio_path):
        audio_model, audio_scaler = load_audio_model(n_classes=2)

        audio_features = extract_audio_features(audio_path)
        audio_result = predict_audio_features(
            audio_features,
            audio_model,
            audio_scaler
        )

        audio_score = audio_result["risk_score"]

    final_report = fuse_scores(
        text_score=text_score,
        audio_score=audio_score
    )

    explanation = explain_text(
        text=text,
        tokenizer=tokenizer,
        model=text_model,
        target_class=text_result["label"]
    )

    return {
        "text_analysis": text_result,
        "text_risk_score": text_score,
        "audio_analysis": audio_result,
        "final_report": final_report,
        "explanation": explanation,
    }


if __name__ == "__main__":
    sample_text = "I feel very sad and hopeless today."

    result = run_prediction(
        text=sample_text,
        audio_path=None
    )

    print(json.dumps(result, indent=4))