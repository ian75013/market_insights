from market_insights.db.models import InsightReport, PriceBar  # noqa: F401
from market_insights.db.session import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
