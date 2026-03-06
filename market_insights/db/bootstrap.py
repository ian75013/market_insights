from market_insights.db.models import Base
from market_insights.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
