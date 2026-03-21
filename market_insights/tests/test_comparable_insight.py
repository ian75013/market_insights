from fastapi.testclient import TestClient

from market_insights.api.main import app

client = TestClient(app)


def test_comparable_insight_endpoint():
    etl = client.post("/etl/run", params={"ticker": "AAPL", "provider": "sample"})
    assert etl.status_code == 200
    response = client.get("/insights/AAPL/comparable")
    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert "summary" in body
    assert body["summary"]["opinion"]
    assert len(body["summary"]["targets"]) == 2
    assert "quotes" in body and "current_price" in body["quotes"]
    assert "technical" in body and "rsi_14" in body["technical"]
    assert "signals" in body and "patterns" in body["signals"]
    assert "disclaimer" in body
