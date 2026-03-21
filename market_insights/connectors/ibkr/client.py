from dataclasses import dataclass
from market_insights.core.config import settings


@dataclass
class IBConnectionConfig:
    host: str = settings.ib_host
    port: int = settings.ib_port
    client_id: int = settings.ib_client_id


class IBClient:
    """Adaptateur minimal pour TWS / IB Gateway.

    Le repo reste démontrable sans dépendance externe: si ib_insync n'est pas installé,
    l'objet existe quand même et les services appellent ensuite le fallback sample.
    """

    def __init__(self, config: IBConnectionConfig | None = None) -> None:
        self.config = config or IBConnectionConfig()
        self._ib = None
        self.available = False
        try:
            from ib_insync import IB  # type: ignore
            self._ib = IB()
            self.available = True
        except Exception:
            self.available = False

    def connect(self) -> bool:
        if not self.available or self._ib is None:
            return False
        if self._ib.isConnected():
            return True
        self._ib.connect(self.config.host, self.config.port, clientId=self.config.client_id)
        return self._ib.isConnected()

    def disconnect(self) -> None:
        if self._ib is not None and self._ib.isConnected():
            self._ib.disconnect()
