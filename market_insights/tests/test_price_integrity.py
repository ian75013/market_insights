"""Tests d'intégrité des prix."""
from sqlalchemy import func, select

from market_insights.db.bootstrap import init_db
from market_insights.db.models import PriceBar
from market_insights.db.session import SessionLocal
from market_insights.services.etl_service import run_etl
from market_insights.services.market_service import MarketInsightService


def _setup():
    init_db()
    db = SessionLocal()
    run_etl(db, "AAPL", provider="sample")
    return db


def test_single_source_after_etl():
    db = _setup()
    try:
        sources = db.execute(
            select(PriceBar.source)
            .where(PriceBar.ticker == "AAPL")
            .distinct()
        ).scalars().all()
        assert len(sources) == 1, f"Multiple sources: {sources}"
    finally:
        db.close()


def test_no_duplicate_dates():
    db = _setup()
    try:
        svc = MarketInsightService()
        df = svc._load_df(db, "AAPL")
        dupes = df[df.duplicated(subset=["date"], keep=False)]
        assert dupes.empty, f"{len(dupes)} doublons"
    finally:
        db.close()


def test_prices_no_jumps():
    db = _setup()
    try:
        svc = MarketInsightService()
        df = svc._load_df(db, "AAPL").sort_values("date")
        for i in range(1, len(df)):
            prev = float(df.iloc[i - 1]["close"])
            curr = float(df.iloc[i]["close"])
            if prev == 0:
                continue
            pct = abs(curr - prev) / prev
            assert pct < 0.20, (
                f"Saut {pct:.1%} entre "
                f"{df.iloc[i-1]['date']} ({prev}) et "
                f"{df.iloc[i]['date']} ({curr})"
            )
    finally:
        db.close()


def test_overwrite_replaces_all():
    db = _setup()
    try:
        count1 = db.execute(
            select(func.count()).where(PriceBar.ticker == "AAPL")
        ).scalar()
        run_etl(db, "AAPL", provider="sample")
        count2 = db.execute(
            select(func.count()).where(PriceBar.ticker == "AAPL")
        ).scalar()
        assert count2 == count1, f"Doublons: {count2} vs {count1}"
    finally:
        db.close()


def test_ohlc_consistency():
    db = _setup()
    try:
        svc = MarketInsightService()
        df = svc._load_df(db, "AAPL")
        for _, row in df.iterrows():
            op = row["open"]
            hi = row["high"]
            lo = row["low"]
            cl = row["close"]
            d = row["date"]
            assert lo <= op, f"{d}: low {lo} > open {op}"
            assert lo <= cl, f"{d}: low {lo} > close {cl}"
            assert hi >= op, f"{d}: high {hi} < open {op}"
            assert hi >= cl, f"{d}: high {hi} < close {cl}"
            assert hi >= lo, f"{d}: high {hi} < low {lo}"
    finally:
        db.close()
