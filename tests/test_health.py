from fastapi.testclient import TestClient

from app.main import app


def test_liveness_without_dependencies():
    response = TestClient(app).get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["stage"] == "scaffold"
