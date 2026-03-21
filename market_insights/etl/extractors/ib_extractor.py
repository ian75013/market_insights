"""Adaptateur IB prévu pour démonstration.

En entretien, tu peux expliquer que cette classe encapsule la connexion réelle à
IB Gateway / TWS via ib_insync, mais qu'on garde ici un fallback pour éviter une
 dépendance runtime dans le repo de démo.
"""

from market_insights.core.logging import get_logger
from market_insights.etl.extractors.sample_extractor import fetch_sample_prices

logger = get_logger(__name__)


def fetch_ib_prices(ticker: str):
    logger.info("Using fallback sample data for IB ticker=%s", ticker)
    return fetch_sample_prices(ticker)
