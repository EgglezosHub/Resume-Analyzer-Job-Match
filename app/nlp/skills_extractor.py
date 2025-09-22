# app/nlp/skills_extractor.py
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

try:
    from rapidfuzz import fuzz
    _HAS_FUZZ = True
except Exception:
    _HAS_FUZZ = False

# -----------------------
# Tunables (be stricter)
# -----------------------
# We do NOT fuzzy-match extremely short or generic tokens.
NO_FUZZ: Set[str] = {
    "api", "git", "sql", "c", "go", "r", "ci", "rpc", "css", "html", "oop"
}
# Min alias length for fuzzy checks (characters)
MIN_FUZZ_LEN = 5
# Fuzzy threshold (partial ratio). 92+ is strict and avoids many false positives.
FUZZ_THRESHOLD = 92
# For multi-word aliases, we require ALL words to appear (with boundaries) before fuzzy fallback.
REQUIRE_ALL_WORDS_BOUNDARY_FIRST = True
# Words that are too generic to be standalone signals (blocked unless part of a longer alias)
GENERIC_SINGLE_TOKENS = {"systems", "development", "software", "programming", "server", "client", "cloud"}

# Canonical -> set(aliases)
_CANONICAL: Dict[str, Set[str]] = {}

# Keep alphanumerics and a few symbols; collapse whitespace.
_WORDISH = re.compile(r"[a-z0-9\-\+\/\._%]+")
def _normalize(text: str) -> str:
    t = text or ""
    t = t.lower()
    toks = _WORDISH.findall(t)
    return " ".join(toks)

def _load_skills_csv(path: Path) -> Dict[str, Set[str]]:
    mapping: Dict[str, Set[str]] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cname = (row.get("skill") or row.get("name") or "").strip().lower()
            if not cname:
                continue
            aliases = {cname}
            raw_aliases = row.get("aliases") or ""
            for a in raw_aliases.split(","):
                a = a.strip().lower()
                if a:
                    aliases.add(a)
            mapping[cname] = aliases
    return mapping

def _ensure_loaded():
    global _CANONICAL
    if _CANONICAL:
        return
    path = Path("data/skills.csv")
    if path.exists():
        _CANONICAL = _load_skills_csv(path)
    else:
        # Minimal fallback. Extend via data/skills.csv in production.
        _CANONICAL = {
            "docker": {"docker", "docker compose", "compose"},
            "linux": {"linux", "gnu/linux"},
            "bash": {"bash", "shell", "sh"},
            "redis": {"redis"},
            "postgresql": {"postgresql", "postgres", "psql"},
            "mysql": {"mysql"},
            "sql": {"sql"},
            "rest api": {"rest api", "restful api", "http api", "rest"},
            "nginx": {"nginx"},
            "git": {"git"},
            "github actions": {"github actions", "actions"},
            "jenkins": {"jenkins", "cicd", "ci/cd"},
            "pytest": {"pytest"},
            "junit": {"junit"},
            "c++": {"c++", "cpp"},
            "c": {"c"},
            "python": {"python", "py"},
            "java": {"java"},
            "socket programming": {"socket programming", "sockets", "tcp", "udp", "network sockets"},
            "communication protocols": {"protocols", "tcp/ip", "grpc", "rpc", "http"},
        }

# ---------- Strict matching helpers ----------

_BOUNDARY_CACHE: Dict[str, re.Pattern] = {}

def _word_boundary_rx(alias: str) -> re.Pattern:
    """Word-boundary regex for alias (multi-word → allow single whitespace)."""
    rx = _BOUNDARY_CACHE.get(alias)
    if rx:
        return rx
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    pattern = rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    rx = re.compile(pattern, re.IGNORECASE)
    _BOUNDARY_CACHE[alias] = rx
    return rx

def _all_words_present(alias: str, text: str) -> bool:
    """Require each token of a multi-word alias to appear as a word (strict)."""
    words = [w for w in alias.split() if w]
    if not words:
        return False
    for w in words:
        if not _word_boundary_rx(w).search(text):
            return False
    return True

def _strict_alias_hit(alias: str, text: str) -> bool:
    """
    Strict rule:
      1) For multi-word alias: ALL words must appear with boundaries (avoids 'api' alone).
      2) For single-word alias: require boundary match. Block extremely generic words.
    """
    alias = alias.strip().lower()
    if not alias:
        return False
    tokens = alias.split()
    if len(tokens) == 1:
        if alias in GENERIC_SINGLE_TOKENS:
            return False
        return bool(_word_boundary_rx(alias).search(text))
    # multi-word
    if REQUIRE_ALL_WORDS_BOUNDARY_FIRST and not _all_words_present(alias, text):
        return False
    return True

def _fuzzy_fallback(alias: str, text: str) -> bool:
    if not _HAS_FUZZ:
        return False
    alias = alias.strip().lower()
    if len(alias) < MIN_FUZZ_LEN or alias in NO_FUZZ:
        return False
    score = fuzz.partial_ratio(alias, text)
    return score >= FUZZ_THRESHOLD

def extract_skills(text: str) -> List[str]:
    """
    Strict, alias-aware extraction:
      - Boundary-aware exact checks first (multi-word → all words).
      - Only then fuzzy for long-enough aliases not in NO_FUZZ.
      - Returns canonical skill names.
    """
    _ensure_loaded()
    body = _normalize(text)
    found: Set[str] = set()
    for canonical, aliases in _CANONICAL.items():
        # If any alias passes strict boundary rules, accept.
        if any(_strict_alias_hit(a, body) for a in aliases):
            found.add(canonical)
            continue
        # Otherwise try fuzzy for long aliases.
        if any(_fuzzy_fallback(a, body) for a in aliases):
            found.add(canonical)
    return sorted(found)

def extract_skills_set(text: str) -> Set[str]:
    return set(extract_skills(text))

