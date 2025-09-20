# app/services/match_service.py
from __future__ import annotations

from typing import List, Set
from sqlalchemy.orm import Session

from app.db.models import Resume, Job, Match
from app.nlp.embeddings import embed
from app.nlp.skills_extractor import extract_skills, extract_skills_set
from app.nlp.similarity import cosine, jaccard
from app.utils.timing import timer

from app.utils.metrics import (
    has_quant_metrics,
    extract_metrics,
    extract_improvements,
    metrics_as_dicts,
    improvements_as_dicts,
)

# Map canonical JD skills -> one concise suggestion line
SKILL_TIPS = {
    "docker": "Highlight Docker/Compose usage (containerize a service or add a Dockerfile/compose.yml).",
    "linux": "Add explicit Linux usage (dev environment, scripting, process/tools).",
    "bash": "Mention Bash/shell scripting if you use it for automation.",
    "redis": "Add a small Redis use (cache/queue) to mirror JD expectations.",
    "postgresql": "Reference PostgreSQL experience (migrations, indexing, joins).",
    "mysql": "Reference MySQL experience (schema design, queries).",
    "sql": "Call out SQL proficiency (joins, indexes, query optimization).",
    "rest api": "State REST API design/implementation experience (auth, validation, pagination).",
    "nginx": "Mention Nginx or HTTP server experience (reverse proxy, static, TLS).",
    "wildfly": "Add WildFly/JBoss exposure if applicable.",
    "lighttpd": "Add Lighttpd familiarity if applicable.",
    "git": "Add Git explicitly if not already (branches, PRs).",
    "jira": "Mention Jira (issues, sprints) for team workflow alignment.",
    "jenkins": "Add CI/CD mention (Jenkins/GitHub Actions) with a short example.",
    "bamboo": "Add CI/CD experience with Bamboo (or equivalent).",
    "pytest": "Mention unit testing with pytest (or add a tests/ folder in repos).",
    "junit": "Mention unit testing with JUnit if you have Java projects.",
    "socket programming": "Emphasize socket programming (TCP/UDP) relevant to JD.",
    "communication protocols": "List relevant protocols (HTTP, RPC, gRPC, TCP/IP).",
    "http server": "Add HTTP server experience (Nginx/Apache/Reverse proxy).",
    "github actions": "Mention CI pipelines (GitHub Actions) for tests/lint/build.",
}

# Keywords that imply “performance focus” in JD
JD_PERF_KW = (
    "performance", "latency", "throughput", "p95", "p99", "optimiz", "ops/sec", "req/s",
    "profil", "benchmark", "rps", "qps"
)

def build_recommendations(resume_text: str, jd_text: str, resume_skills: Set[str], jd_skills: Set[str]) -> List[str]:
    """
    ONLY suggest items that appear in the JD but are missing from the resume (skills and themes).
    Also: suggest adding metrics ONLY if JD is performance-focused AND resume has no quant metrics.
    """
    tips: List[str] = []
    # Skills in JD but not in resume -> suggestions
    missing_skills = sorted(jd_skills - resume_skills)
    for s in missing_skills:
        if s in SKILL_TIPS:
            tips.append(SKILL_TIPS[s])

    # Performance/metrics suggestion (JD-driven + resume lacks metrics)
    jd_lower = (jd_text or "").lower()
    if any(k in jd_lower for k in JD_PERF_KW):
        if not has_quant_metrics(resume_text):
            tips.append("Quantify performance (e.g., req/s, ops/sec, p95 ms, error %, users) for at least one project.")

    # De-duplicate while preserving order
    seen = set()
    uniq = []
    for t in tips:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def pick_missing(resume_skills: List[str], job_text: str) -> List[str]:
    """
    Canonical 'missing' list strictly from JD minus resume (alphabetical).
    """
    jd_sk = extract_skills_set(job_text)
    r_sk = {s.lower() for s in resume_skills}
    missing = sorted(list(jd_sk - r_sk))
    return missing[:8]  # show a bit more now that tips are precise


def match_resume_job(db: Session, resume: Resume, job: Job) -> dict:
    """
    Main routine:
    - Semantic similarity via SBERT vectors.
    - Skill overlap via Jaccard over canonical skill sets.
    - Match score (blend).
    - Suggestions: ONLY JD-missing items, plus metrics if JD is perf-focused and resume lacks metrics.
    """
    with timer() as elapsed:
        # Vectors & similarity
        r_vec = embed(resume.text)
        j_vec = embed(job.description)
        sim = cosine(r_vec, j_vec)

        # Skill sets
        r_sk = extract_skills_set(resume.text)
        j_sk = extract_skills_set(job.description)
        overlap = jaccard(r_sk, j_sk)

        # Composite score
        match_score = 0.7 * sim + 0.3 * overlap

        # Missing + targeted tips
        missing = sorted(list(j_sk - r_sk))
        recs = build_recommendations(resume.text, job.description, r_sk, j_sk)

        # Optional visibility: parsed metrics & improvements from resume
        parsed_metrics = metrics_as_dicts(extract_metrics(resume.text))
        improvements = improvements_as_dicts(extract_improvements(resume.text))

        runtime = elapsed()

    # Persist
    m = Match(
        resume_id=resume.id,
        job_id=job.id,
        similarity=float(sim),
        skill_overlap=float(overlap),
        match_score=float(match_score),
        missing_skills=missing,
        recommendations=recs,
        runtime_ms=runtime,
    )
    db.add(m); db.commit(); db.refresh(m)

    return {
        "resume_id": resume.id,
        "job_id": job.id,
        "match_score": round(float(match_score), 3),
        "semantic_similarity": round(float(sim), 3),
        "skill_overlap": round(float(overlap), 3),
        "missing_skills": missing,           # strictly JD minus resume
        "recommendations": recs,             # only JD-driven + metrics-if-relevant
        "runtime_ms": runtime,
        "parsed_metrics": parsed_metrics,    # optional: helpful for UI/debug
        "improvements": improvements,        # optional: helpful for UI/debug
    }

