from fastapi.testclient import TestClient

from market_insights.api.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_etl_then_insight():
    etl = client.post("/etl/run", params={"ticker": "AAPL", "provider": "sample"})
    assert etl.status_code == 200
    response = client.get("/insights/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert "analysis" in body
    assert len(body["sources"]) >= 1


def test_sources_endpoint():
    response = client.get("/sources")
    assert response.status_code == 200
    assert "ibkr" in response.json()["price_providers"]
