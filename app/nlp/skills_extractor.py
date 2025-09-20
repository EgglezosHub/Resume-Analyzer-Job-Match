# app/nlp/skills_extractor.py
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Robust, alias-aware + fuzzy matching extractor.
# - Reads data/skills.csv with columns: skill,aliases
# - Matches exact substrings OR fuzzy (tolerates typos like "doccer" -> docker)
# - Returns canonical skills (lowercase)

try:
    from rapidfuzz import fuzz
    _HAS_FUZZ = True
except Exception:
    _HAS_FUZZ = False

# Canonical skill -> set(aliases)
_CANONICAL: Dict[str, Set[str]] = {}

WORDISH = re.compile(r"[a-z0-9\-\+\/\._%]+")

def _normalize(text: str) -> str:
    # keep word-ish characters only; collapse whitespace
    t = text or ""
    t = t.lower()
    toks = WORDISH.findall(t)
    return " ".join(toks)

def _load_skills_csv(path: Path) -> Dict[str, Set[str]]:
    mapping: Dict[str, Set[str]] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Accept either 'skill' or 'name' for compatibility
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
    if not path.exists():
        # Minimal fallback set if csv is missing
        _CANONICAL = {
            "docker": {"docker", "docker compose", "compose"},
            "linux": {"linux", "gnu/linux"},
            "bash": {"bash", "shell", "sh"},
            "redis": {"redis", "nosql cache"},
            "postgresql": {"postgresql", "postgres", "psql"},
            "mysql": {"mysql"},
            "sql": {"sql"},
            "rest api": {"rest", "restful", "api", "http api"},
            "nginx": {"nginx"},
            "wildfly": {"wildfly", "jboss"},
            "lighttpd": {"lighttpd"},
            "git": {"git"},
            "jira": {"jira"},
            "jenkins": {"jenkins", "ci/cd", "cicd"},
            "bamboo": {"bamboo"},
            "pytest": {"pytest", "unit testing", "tests"},
            "junit": {"junit"},
            "c++": {"c++", "cpp"},
            "c": {"c"},
            "python": {"python"},
            "socket programming": {"socket programming", "sockets", "tcp", "udp"},
            "communication protocols": {"protocols", "tcp/ip", "http", "grpc", "rpc"},
        }
    else:
        _CANONICAL = _load_skills_csv(path)

def _match_alias_in_text(alias: str, text: str, fuzzy_threshold: int = 88) -> bool:
    # exact containment first
    if alias in text:
        return True
    # fuzzy fallback (if available)
    if _HAS_FUZZ:
        # partial ratio against the whole text is heavy; optimize by sliding window over words
        # quick heuristic: only fuzzy if alias length >= 4
        if len(alias) >= 4:
            score = fuzz.partial_ratio(alias, text)
            return score >= fuzzy_threshold
    return False

def extract_skills(text: str) -> List[str]:
    """
    Return a sorted list of canonical skills detected in text.
    Alias-aware, fuzzy tolerant.
    """
    _ensure_loaded()
    body = _normalize(text)
    found: Set[str] = set()
    for canonical, aliases in _CANONICAL.items():
        # If any alias roughly appears, mark canonical
        if any(_match_alias_in_text(a, body) for a in aliases):
            found.add(canonical)
    return sorted(found)

def extract_skills_set(text: str) -> Set[str]:
    return set(extract_skills(text))

