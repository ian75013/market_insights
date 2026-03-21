"""Extractive summarizer + HTML stripper — zéro dépendance lourde."""
from __future__ import annotations
import re
from collections import Counter
from html.parser import HTMLParser

class _Strip(HTMLParser):
    def __init__(self):
        super().__init__()
        self._t: list[str] = []
    def handle_data(self, d):
        self._t.append(d)
    def get(self) -> str:
        return " ".join(self._t)

def strip_html(text: str) -> str:
    if not text:
        return ""
    s = _Strip()
    try:
        s.feed(text)
        return re.sub(r"\s+", " ", s.get()).strip()
    except Exception:
        return re.sub(r"<[^>]+>", " ", text).strip()

_STOP = frozenset("the and or a an of to in for with on at by is it that this was are be has have had will can may from its as but not their we he she they our le la les de du des un une et en à pour par sur est ce qui que dans son sa ses avec ne pas au aux cette".split())

def _tok(t: str) -> list[str]:
    return [w for w in re.findall(r"\b[a-zà-ÿ]{2,}\b", t.lower()) if w not in _STOP]

def summarize(text: str, max_sentences: int = 2, max_chars: int = 250) -> str:
    text = strip_html(text)
    if not text or len(text) < 80:
        return text
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if len(s.strip()) > 25]
    if len(sents) <= max_sentences:
        r = " ".join(sents)
        return r[:max_chars] + "…" if len(r) > max_chars else r
    tf = Counter(_tok(text))
    mx = max(tf.values()) or 1
    scored = []
    for i, s in enumerate(sents):
        toks = _tok(s)
        if not toks:
            continue
        sc = sum(tf.get(t, 0) / mx for t in toks) / len(toks)
        if i == 0: sc *= 1.15
        if re.search(r"\d", s): sc *= 1.1
        scored.append((sc, i, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = sorted(scored[:max_sentences], key=lambda x: x[1])
    r = " ".join(p[2] for p in picked)
    return r[:max_chars] + "…" if len(r) > max_chars else r
