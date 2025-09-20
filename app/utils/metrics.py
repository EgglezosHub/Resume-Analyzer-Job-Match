# app/utils/metrics.py
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Iterable, List, Optional, Tuple

@dataclass
class Metric:
    kind: str
    value: Optional[float]
    unit: Optional[str]
    raw: str
    qualifier: Optional[str]
    span: Tuple[int, int]
    context: str

@dataclass
class Improvement:
    metric_kind: str
    before: Optional[float]
    after: Optional[float]
    unit: Optional[str]
    raw: str
    delta_pct: Optional[float]
    direction: Optional[str]
    span: Tuple[int, int]

_WS = re.compile(r"\s+")
def _norm_space(s: str) -> str:
    return _WS.sub(" ", s).strip()

def _preprocess(text: str) -> str:
    if not text:
        return ""
    reps = {"≤": "<=", "≥": ">=", "→": "->", "⇒": "->", "–": "-", "—": "-", "≈": "~", "％": "%", "\u00a0": " "}
    for k, v in reps.items():
        text = text.replace(k, v)
    return _norm_space(text)

_NUM_TOKEN = r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
_NUM_KMB   = r"(?:k|m|b|K|M|B)\b"
_WORD_MAG  = r"(?:thousand|million|billion)\b"
_MAG_MAP   = {"k": 1e3,"K": 1e3,"thousand":1e3,"m":1e6,"M":1e6,"million":1e6,"b":1e9,"B":1e9,"billion":1e9}

def _to_float(num_str: str) -> float: return float(num_str.replace(",", "_"))
def _apply_magnitude(v: float, mag: Optional[str]) -> float: return v * _MAG_MAP.get((mag or "").strip(), 1.0)

def parse_number(token: str) -> Optional[float]:
    token = token.strip()
    m = re.fullmatch(rf"({_NUM_TOKEN})\s*({_NUM_KMB})", token)
    if m: return _apply_magnitude(_to_float(m.group(1)), m.group(2))
    m = re.fullmatch(rf"({_NUM_TOKEN})\s*({_WORD_MAG})", token, flags=re.IGNORECASE)
    if m: return _apply_magnitude(_to_float(m.group(1)), m.group(2).lower())
    m = re.fullmatch(rf"{_NUM_TOKEN}", token)
    if m: return _to_float(m.group(0))
    return None

KW_AVAIL = ("availability","uptime","slo","sli","apdex")
KW_ERRORS= ("error rate","errors","failures","0% failure","failure rate")

RE_PERCENT  = re.compile(rf"(?P<num>{_NUM_TOKEN})\s?%")
RE_LAT_MS   = re.compile(rf"(?P<num>{_NUM_TOKEN})\s?ms\b", re.IGNORECASE)
RE_LAT_S    = re.compile(rf"(?P<num>{_NUM_TOKEN})\s?s(ec|econd|)\b", re.IGNORECASE)
RE_RATE     = re.compile(
    rf"(?P<num>{_NUM_TOKEN})\s?(?P<unit>rps|qps|req/s|req/sec|requests/s|requests/sec|ops/s|ops/sec|operations/s|operations/sec|msgs/s|msgs/sec|messages/s|messages/sec|writes/s|reads/s|queries/s|queries/sec|events/s|events/sec)\b",
    re.IGNORECASE
)
RE_COUNT_NOUN = re.compile(
    rf"(?P<num>{_NUM_TOKEN})(?:\s*(?P<mag>{_NUM_KMB}|{_WORD_MAG}))?\s+(?P<noun>users|concurrent users|visitors|pageviews|page views|sessions|clients)\b",
    re.IGNORECASE
)
RE_RESOURCE_BYTES = re.compile(rf"(?P<num>{_NUM_TOKEN})\s?(?P<unit>kb|mb|gb)\b", re.IGNORECASE)
RE_RESOURCE_CPU   = re.compile(rf"(?P<num>{_NUM_TOKEN})\s?%\s?(cpu|utilization)?\b", re.IGNORECASE)
RE_QUAL_LAT = re.compile(
    rf"(?P<qual>p50|p75|p90|p95|p99|p999|median|avg|average|p\.?95|p\.?99)\s*(?:<=|>=|<|>|=|~)?\s*(?P<num>{_NUM_TOKEN})\s?(?P<unit>ms|s)\b",
    re.IGNORECASE
)
RE_LAT_CMP  = re.compile(rf"(?P<op><=|>=|<|>)\s*(?P<num>{_NUM_TOKEN})\s?(?P<unit>ms|s)\b", re.IGNORECASE)
RE_DELTA_ARROW = re.compile(rf"(?P<before>{_NUM_TOKEN}\s?(?:ms|s))\s*(?:->|to)\s*(?P<after>{_NUM_TOKEN}\s?(?:ms|s))", re.IGNORECASE)
RE_DELTA_WORD  = re.compile(rf"(reduced|decreased|improved)\s+(?:from\s+(?P<before>{_NUM_TOKEN}\s?(?:ms|s))\s+to\s+(?P<after>{_NUM_TOKEN}\s?(?:ms|s))|by\s+(?P<pct>{_NUM_TOKEN})\s?%)", re.IGNORECASE)

def _to_ms(value: float, unit: str) -> float:
    unit = unit.lower()
    if unit.startswith("ms"): return value
    if unit.startswith("s"):  return value * 1000.0
    return value

def _rate_unit_to_rps(_: str) -> str: return "rps"

def _bytes_unit_to_mb(value: float, unit: str) -> float:
    unit = unit.lower()
    if unit == "kb": return value / 1024.0
    if unit == "mb": return value
    if unit == "gb": return value * 1024.0
    return value

def _ctx(text: str, start: int, end: int, pad: int = 40) -> str:
    lo = max(0, start - pad); hi = min(len(text), end + pad); return text[lo:hi]

def _has_any(s: str, kws) -> bool:
    s = s.lower()
    return any(k in s for k in kws)

def has_quant_metrics(text: str) -> bool:
    t = _preprocess(text)
    return any((
        RE_PERCENT.search(t),
        RE_RATE.search(t),
        RE_QUAL_LAT.search(t) or RE_LAT_MS.search(t) or RE_LAT_S.search(t) or RE_LAT_CMP.search(t),
        RE_COUNT_NOUN.search(t),
        RE_RESOURCE_BYTES.search(t) or RE_RESOURCE_CPU.search(t),
        RE_DELTA_ARROW.search(t) or RE_DELTA_WORD.search(t),
    ))

def extract_metrics(text: str) -> List[Metric]:
    out: List[Metric] = []
    src = _preprocess(text)

    for m in RE_PERCENT.finditer(src):
        val = parse_number(m.group("num")) or 0.0
        window = _ctx(src, m.start(), m.end())
        kind = "percent"
        if _has_any(window, KW_AVAIL): kind = "availability"
        elif _has_any(window, KW_ERRORS): kind = "errors"
        out.append(Metric(kind=kind, value=val, unit="%", raw=m.group(0),
                          qualifier=None, span=(m.start(), m.end()), context=window))

    for m in RE_RATE.finditer(src):
        val = parse_number(m.group("num")) or 0.0
        unit = _rate_unit_to_rps(m.group("unit"))
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="throughput", value=val, unit=unit, raw=m.group(0),
                          qualifier=None, span=(m.start(), m.end()), context=window))

    for m in RE_QUAL_LAT.finditer(src):
        num = parse_number(m.group("num")) or 0.0
        ms = _to_ms(num, m.group("unit"))
        qual = m.group("qual").lower().replace(".", "")
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="latency", value=ms, unit="ms", raw=m.group(0),
                          qualifier=qual, span=(m.start(), m.end()), context=window))

    for m in RE_LAT_MS.finditer(src):
        ms = parse_number(m.group("num")) or 0.0
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="latency", value=ms, unit="ms", raw=m.group(0),
                          qualifier=None, span=(m.start(), m.end()), context=window))

    for m in RE_LAT_S.finditer(src):
        s_val = parse_number(m.group("num")) or 0.0
        ms = _to_ms(s_val, "s")
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="latency", value=ms, unit="ms", raw=m.group(0),
                          qualifier=None, span=(m.start(), m.end()), context=window))

    for m in RE_LAT_CMP.finditer(src):
        num = parse_number(m.group("num")) or 0.0
        ms = _to_ms(num, m.group("unit"))
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="latency", value=ms, unit="ms", raw=m.group(0),
                          qualifier=m.group("op"), span=(m.start(), m.end()), context=window))

    for m in RE_COUNT_NOUN.finditer(src):
        num = parse_number(m.group("num")) or 0.0
        mag = m.group("mag") or ""
        if mag: num = _apply_magnitude(num, mag)
        noun = m.group("noun").lower()
        unit = "users" if ("user" in noun or "client" in noun) else ("pageviews" if "page" in noun else noun)
        qual = "concurrent" if "concurrent" in noun else None
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="users", value=float(num), unit=unit, raw=m.group(0),
                          qualifier=qual, span=(m.start(), m.end()), context=window))

    for m in RE_RESOURCE_BYTES.finditer(src):
        num = parse_number(m.group("num")) or 0.0
        mb = _bytes_unit_to_mb(num, m.group("unit"))
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="resource", value=mb, unit="MB", raw=m.group(0),
                          qualifier="memory", span=(m.start(), m.end()), context=window))

    for m in RE_RESOURCE_CPU.finditer(src):
        val = parse_number(m.group("num")) or 0.0
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="resource", value=val, unit="%", raw=m.group(0),
                          qualifier="cpu", span=(m.start(), m.end()), context=window))

    extra_rate = re.compile(
        rf"(?P<num>{_NUM_TOKEN})\s+(?P<phrase>requests per second|operations per second|queries per second|messages per second)",
        re.IGNORECASE,
    )
    for m in extra_rate.finditer(src):
        val = parse_number(m.group("num")) or 0.0
        window = _ctx(src, m.start(), m.end())
        out.append(Metric(kind="throughput", value=val, unit="rps", raw=m.group(0),
                          qualifier=None, span=(m.start(), m.end()), context=window))

    return _dedupe(out)

def extract_improvements(text: str) -> List[Improvement]:
    out: List[Improvement] = []
    src = _preprocess(text)

    RE_DELTA_ARROW = re.compile(rf"(?P<before>{_NUM_TOKEN}\s?(?:ms|s))\s*(?:->|to)\s*(?P<after>{_NUM_TOKEN}\s?(?:ms|s))", re.IGNORECASE)
    RE_DELTA_WORD  = re.compile(rf"(reduced|decreased|improved)\s+(?:from\s+(?P<before>{_NUM_TOKEN}\s?(?:ms|s))\s+to\s+(?P<after>{_NUM_TOKEN}\s?(?:ms|s))|by\s+(?P<pct>{_NUM_TOKEN})\s?%)", re.IGNORECASE)

    def _split_num_unit(tok: str):
        tok = tok.strip()
        m = re.fullmatch(rf"\s*({_NUM_TOKEN})\s*(ms|s)?\s*", tok, flags=re.IGNORECASE)
        if not m: return None, None
        v = parse_number(m.group(1)); unit = (m.group(2) or "").lower() or None
        return v, unit

    def _to_ms(value: float, unit: str) -> float:
        unit = unit or ""
        if unit.startswith("ms"): return value
        if unit.startswith("s"):  return value * 1000.0
        return value

    def _pct_change(before: float, after: float):
        if before == 0: return None
        return ((before - after) / before) * 100.0

    for m in RE_DELTA_ARROW.finditer(src):
        b_num, b_unit = _split_num_unit(m.group("before"))
        a_num, a_unit = _split_num_unit(m.group("after"))
        if b_num is None or a_num is None: continue
        unit = "ms" if (b_unit in ("ms", "s") or a_unit in ("ms", "s")) else (b_unit or a_unit)
        b_norm = _to_ms(b_num, b_unit) if unit == "ms" else b_num
        a_norm = _to_ms(a_num, a_unit) if unit == "ms" else a_num
        pct = _pct_change(b_norm, a_norm)
        out.append(Improvement("latency", b_norm, a_norm, unit, m.group(0), pct, "reduction" if a_norm < b_norm else "increase", (m.start(), m.end())))

    for m in RE_DELTA_WORD.finditer(src):
        verb = m.group(1).lower()
        before_tok = m.group("before"); after_tok = m.group("after"); pct_tok = m.group("pct")
        if pct_tok:
            pct = parse_number(pct_tok) or 0.0
            out.append(Improvement("percent", None, None, "%", m.group(0), pct, "improvement" if verb == "improved" else "reduction", (m.start(), m.end())))
        elif before_tok and after_tok:
            b_num, b_unit = _split_num_unit(before_tok); a_num, a_unit = _split_num_unit(after_tok)
            if b_num is None or a_num is None: continue
            unit = "ms" if (b_unit in ("ms","s") or a_unit in ("ms","s")) else (b_unit or a_unit)
            b_norm = _to_ms(b_num, b_unit) if unit == "ms" else b_num
            a_norm = _to_ms(a_num, a_unit) if unit == "ms" else a_num
            pct = ((b_norm - a_norm)/b_norm)*100.0 if b_norm else None
            out.append(Improvement("latency", b_norm, a_norm, unit, m.group(0), pct, "improvement" if verb == "improved" else "reduction", (m.start(), m.end())))

    return out

def _dedupe(items: List[Metric]) -> List[Metric]:
    seen = set(); out = []
    for it in items:
        key = (it.kind, it.span, it.raw)
        if key in seen: continue
        seen.add(key); out.append(it)
    return out

def metrics_as_dicts(metrics: List[Metric]) -> List[dict]:
    return [asdict(m) for m in metrics]

def improvements_as_dicts(imps: List[Improvement]) -> List[dict]:
    return [asdict(i) for i in imps]

