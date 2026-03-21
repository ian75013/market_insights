from fastapi.testclient import TestClient
from market_insights.api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "4.0.0"


def test_sources_endpoint():
    response = client.get("/sources")
    assert response.status_code == 200
    body = response.json()
    assert "yahoo" in body["price_providers"]
    assert "auto" in body["price_providers"]
    assert "multi" in body["fundamentals_providers"]


def test_providers_endpoint():
    response = client.get("/providers")
    assert response.status_code == 200
    body = response.json()
    assert "price_providers" in body
    assert "api_keys_configured" in body


def test_etl_then_insight():
    etl = client.post("/etl/run", params={"ticker": "AAPL", "provider": "sample"})
    assert etl.status_code == 200
    etl_body = etl.json()
    assert etl_body["loaded_rows"] > 0

    response = client.get("/insights/AAPL")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert "analysis" in body
    assert len(body["sources"]) >= 1


def test_etl_batch():
    etl = client.post("/etl/batch", params={"tickers": "MSFT,NVDA", "provider": "sample"})
    assert etl.status_code == 200
    body = etl.json()
    assert len(body) == 2
    assert body[0]["ticker"] in ("MSFT", "NVDA")


def test_fair_value():
    client.post("/etl/run", params={"ticker": "GOOGL", "provider": "sample"})
    response = client.get("/fair-value/GOOGL")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "GOOGL"
    assert body["fair_value"] > 0
    assert "method" in body


def test_hybrid_insight():
    client.post("/etl/run", params={"ticker": "AAPL", "provider": "sample"})
    response = client.get("/insights/AAPL/hybrid")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["verdict"] in ("bullish", "bearish", "neutral")
    assert "executive_summary" in body
    assert "rag" in body


def test_comparable_insight():
    client.post("/etl/run", params={"ticker": "AAPL", "provider": "sample"})
    response = client.get("/insights/AAPL/comparable")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert "summary" in body


def test_fundamentals_endpoint():
    response = client.get("/fundamentals/AAPL")
    assert response.status_code == 200


def test_macro_endpoint():
    response = client.get("/macro")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] in ("sample", "fred")


def test_cache_stats():
    response = client.get("/cache/stats")
    assert response.status_code == 200
    body = response.json()
    assert "total_keys" in body
