from fastapi.testclient import TestClient

from apt_hunter.main import app

client = TestClient(app)


def test_liveness() -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "apt-hunter-api",
        "version": "1.0.0",
    }


def test_prometheus_metrics_are_exposed_outside_the_public_api_prefix() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "apt_hunter_http_requests_total" in response.text
    assert "apt_hunter_dependency_up" in response.text
