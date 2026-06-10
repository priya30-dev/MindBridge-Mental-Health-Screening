import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from api.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        resp = client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_text_analyse_low_risk():
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/text/analyse",
            json={
                "text": "I am doing well today, feeling positive.",
                "explain": False
            }
        )

        assert resp.status_code == 200
        data = resp.json()

        assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert 0 <= data["risk_score"] <= 100


def test_text_analyse_with_explanation():
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/text/analyse",
            json={
                "text": "Everything feels pointless and I can't go on.",
                "explain": True
            }
        )

        assert resp.status_code == 200
        data = resp.json()

        assert "top_tokens" in data