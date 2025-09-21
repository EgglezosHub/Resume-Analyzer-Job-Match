# app/services/match_service.py
from __future__ import annotations
from typing import List, Set
from sqlalchemy.orm import Session

from app.db.models import Resume, Job, Match
from app.nlp.embeddings import embed
from app.nlp.skills_extractor import extract_skills, extract_skills_set
from app.nlp.similarity import cosine
from app.utils.timing import timer
from app.utils.metrics import (
    has_quant_metrics,
    extract_metrics, extract_improvements,
    metrics_as_dicts, improvements_as_dicts,
)

SKILL_TIPS = {
    "docker": "Highlight Docker/Compose usage (containerize a service or add a Dockerfile/compose.yml).",
    "linux": "Add explicit Linux usage (dev environment, scripting, process/tools).",
    "bash": "Mention Bash/shell scripting if you use it for automation.",
    "redis": "Add a small Redis usage (cache/queue) to mirror JD expectations.",
    "postgresql": "Reference PostgreSQL experience (migrations, indexing, joins).",
    "mysql": "Reference MySQL experience (schema design, queries).",
    "sql": "Call out SQL proficiency (joins, indexes, query optimization).",
    "rest api": "State REST API design/implementation experience (auth, validation, pagination).",
    "nginx": "Mention Nginx or HTTP server experience (reverse proxy, static, TLS).",
    "git": "Add Git explicitly if not already (branches, PRs).",
    "github actions": "Mention CI pipelines (GitHub Actions) for tests/lint/build.",
    "jenkins": "Add CI/CD mention (Jenkins/GitHub Actions) with a short example.",
    "pytest": "Mention unit testing with pytest (or add a tests/ folder in repos).",
    "junit": "Mention unit testing with JUnit if you have Java projects.",
    "c++": "Emphasize modern C++ usage (STL, concurrency) if relevant to the role.",
    "c": "Call out C experience when low-level/performance is required.",
    "python": "List Python projects (APIs, scripts, data tooling) if applicable.",
    "java": "Add Java experience if relevant (Spring/Spring Boot).",
    "spring boot": "Mention Spring Boot/Spring Framework experience.",
    "aws": "Call out AWS usage (EC2/Lambda/S3/IAM/Terraform) if you have it.",
    "terraform": "Add Terraform/IaC details (modules, workspaces, plans/apply).",
    "react": "Mention React/SPA experience (hooks, routing, state mgmt).",
    "socket programming": "Emphasize socket programming (TCP/UDP) relevant to JD.",
    "communication protocols": "List relevant protocols (HTTP, RPC, gRPC, TCP/IP).",
}

JD_PERF_KW = ("performance", "latency", "throughput", "p95", "p99", "ops/sec", "req/s", "rps", "qps")
SIM_UNRELATED_CLAMP = 0.20

def _jd_coverage(r_sk: Set[str], j_sk: Set[str]) -> float:
    if not j_sk:
        return 0.0
    return len(r_sk & j_sk) / float(len(j_sk))

def build_recommendations(resume_text: str, jd_text: str, resume_skills: Set[str], jd_skills: Set[str]) -> List[str]:
    tips: List[str] = []
    for s in sorted(jd_skills - resume_skills):
        if s in SKILL_TIPS:
            tips.append(SKILL_TIPS[s])

    jd_lower = (jd_text or "").lower()
    if any(k in jd_lower for k in JD_PERF_KW) and not has_quant_metrics(resume_text):
        tips.append("Quantify performance (e.g., req/s, ops/sec, p95 ms, error %, users) for at least one project.")

    # de-dupe
    seen = set(); out=[]
    for t in tips:
        if t not in seen:
            seen.add(t); out.append(t)
    return out

def match_resume_job(db: Session, resume: Resume, job: Job) -> dict:
    """
    Strict scoring:
      - semantic similarity (embeddings + cosine)
      - JD Skill Coverage = |resume ∩ JD| / |JD|
      - composite = 0.7 * sim + 0.3 * coverage
      - if coverage == 0 and sim < clamp → hard 0 (unrelated)
    """
    with timer() as elapsed:
        r_vec = embed(resume.text)
        j_vec = embed(job.description)
        sim = float(cosine(r_vec, j_vec))

        r_sk = extract_skills_set(resume.text)
        j_sk = extract_skills_set(job.description)

        coverage = float(_jd_coverage(r_sk, j_sk))
        match_score = 0.7 * sim + 0.3 * coverage
        if coverage == 0.0 and sim < SIM_UNRELATED_CLAMP:
            match_score = 0.0

        missing = sorted(list(j_sk - r_sk))
        recs = build_recommendations(resume.text, job.description, r_sk, j_sk)

        parsed_metrics = metrics_as_dicts(extract_metrics(resume.text))
        improvements = improvements_as_dicts(extract_improvements(resume.text))
        runtime = elapsed()

    m = Match(
        resume_id=resume.id, job_id=job.id,
        similarity=sim, skill_overlap=coverage, match_score=match_score,
        missing_skills=missing, recommendations=recs, runtime_ms=runtime,
    )
    db.add(m); db.commit(); db.refresh(m)

    return {
        "resume_id": resume.id,
        "job_id": job.id,
        "match_score": round(match_score, 3),
        "semantic_similarity": round(sim, 3),
        "skill_overlap": round(coverage, 3),    # JD Skill Coverage
        "jd_skills": sorted(list(j_sk)),        # <-- expose JD skills
        "resume_skills": sorted(list(r_sk)),    # optional, useful in UI
        "missing_skills": missing,
        "recommendations": recs,
        "runtime_ms": runtime,
        "parsed_metrics": parsed_metrics,
        "improvements": improvements,
    }

