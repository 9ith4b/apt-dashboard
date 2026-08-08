from fastapi.testclient import TestClient

from apt_hunter.main import app

client = TestClient(app)


def test_liveness() -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "apt-hunter-api",
        "version": "0.1.0",
    }
