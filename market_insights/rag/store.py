from pathlib import Path


DOCS_PATH = Path(__file__).resolve().parents[1] / "data" / "sample" / "knowledge_base.txt"


def retrieve_context(ticker: str, top_k: int = 3) -> list[str]:
    lines = DOCS_PATH.read_text(encoding="utf-8").splitlines()
    relevant = [line for line in lines if ticker.upper() in line.upper() or line.startswith("GENERAL:")]
    return relevant[:top_k]
