"""FastAPI classification endpoint contract checks."""
from fastapi.testclient import TestClient
from agents.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"


def test_classify_endpoint():
    response = client.post("/api/classify", json={"egfr": 52, "acr_mg_g": 125})
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "G3aA2"
    assert data["risk_category"] == "high"
    assert data["ckd_confirmed"] is None


def test_invalid_values_rejected():
    for body in ({"egfr": -1, "acr_mg_g": 45},
                 {"egfr": 45, "acr_mg_g": -1},
                 {"egfr": "nan", "acr_mg_g": 30},
                 {"egfr": 52}):
        assert client.post("/api/classify", json=body).status_code == 422


def test_unconfigured_mock_does_not_claim_verification():
    response = client.post("/api/chat", json={"query": "What is this?"})
    assert response.status_code == 200
    assert "No language model" in response.json()["response"]
