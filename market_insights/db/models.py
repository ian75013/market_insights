from sqlalchemy import Column, Date, Float, Integer, String, Text

from market_insights.db.session import Base


class PriceBar(Base):
    __tablename__ = "price_bars"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(16), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)


class InsightReport(Base):
    __tablename__ = "insight_reports"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(16), index=True, nullable=False)
    created_at = Column(String(32), nullable=False)
    summary = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    fair_value = Column(Float, nullable=False)
