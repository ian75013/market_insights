from sqlalchemy.orm import Session

from market_insights.etl.extractors.ib_extractor import fetch_ib_prices
from market_insights.etl.transformers.cleaning import clean_market_data
from market_insights.etl.transformers.features import compute_features
from market_insights.etl.loaders.sqlite_loader import load_price_bars


def run_etl(db: Session, ticker: str) -> dict:
    raw = fetch_ib_prices(ticker)
    clean = clean_market_data(raw)
    featured = compute_features(clean)

    rows = [
        {
            "ticker": row["ticker"],
            "date": row["date"].date(),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for _, row in clean.iterrows()
    ]
    loaded = load_price_bars(db, ticker, rows)
    return {"ticker": ticker, "loaded_rows": loaded, "feature_rows": len(featured)}
