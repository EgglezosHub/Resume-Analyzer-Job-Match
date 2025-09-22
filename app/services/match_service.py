from __future__ import annotations
from typing import List, Set
from sqlalchemy.orm import Session

from app.db.models import Resume, Job, Match
from app.nlp.embeddings import embed
from app.nlp.skills_extractor import extract_skills_set
from app.nlp.similarity import cosine
from app.utils.timing import timer
from app.utils.metrics import (
    has_quant_metrics, extract_metrics, extract_improvements,
    metrics_as_dicts, improvements_as_dicts,
)

# Targeted content-aware recommendations (Smart tips v2)
TIP_GROUPS = {
    "cloud": {
        "keys": {"aws","gcp","azure"},
        "tip": "Add a minimal cloud section (e.g., deploy a demo to AWS/GCP/Azure: service, IaC, monitoring)."
    },
    "iac": {
        "keys": {"terraform","pulumi","cloudformation"},
        "tip": "Show Infrastructure-as-Code (Terraform/Pulumi) with one environment module and a plan/apply example."
    },
    "java_spring": {
        "keys": {"java","spring boot"},
        "tip": "Include a small Spring Boot REST API (auth, validation, pagination)."
    },
    "frontend_react": {
        "keys": {"react","vue","angular"},
        "tip": "If relevant, add a simple frontend (React/Vue/Angular) talking to your API."
    },
    "devops": {
        "keys": {"docker","kubernetes","helm","github actions","jenkins","gitlab ci"},
        "tip": "Document your delivery pipeline: Dockerfile, Compose/Helm, and one CI workflow for tests/build."
    }
}

JD_PERF_KW = ("performance","latency","throughput","p95","p99","ops/sec","req/s","rps","qps")
SIM_UNRELATED_CLAMP = 0.20

def _jd_coverage(r_sk: Set[str], j_sk: Set[str]) -> float:
    if not j_sk:
        return 0.0
    return len(r_sk & j_sk) / float(len(j_sk))

def _smart_tips_v2(resume_sk: Set[str], jd_sk: Set[str], resume_text: str, jd_text: str) -> List[str]:
    tips: List[str] = []

    # Specific gaps (JD skill missing in resume)
    missing = sorted(list(jd_sk - resume_sk))
    for g in missing:
        # a generic per-skill hint:
        tips.append(f"Add or highlight **{g}** experience if relevant to this role.")

    # Content-aware groups (cloud/IaC/frameworks/DevOps)
    for grp in TIP_GROUPS.values():
        if grp["keys"] & jd_sk and not (grp["keys"] & resume_sk):
            tips.append(grp["tip"])

    # Performance metrics encouragement when JD cares and resume lacks
    jd_lower = (jd_text or "").lower()
    if any(k in jd_lower for k in JD_PERF_KW) and not has_quant_metrics(resume_text):
        tips.append("Quantify performance (req/s, ops/sec, p95 ms, error %, users) in at least one project.")

    # de-dupe
    seen = set(); uniq=[]
    for t in tips:
        if t not in seen:
            seen.add(t); uniq.append(t)
    return uniq

def match_resume_job(db: Session, resume: Resume, job: Job) -> dict:
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

        recs = _smart_tips_v2(r_sk, j_sk, resume.text, job.description)

        parsed_metrics = metrics_as_dicts(extract_metrics(resume.text))
        improvements = improvements_as_dicts(extract_improvements(resume.text))
        runtime = elapsed()

    m = Match(
        resume_id=resume.id, job_id=job.id,
        similarity=sim, skill_overlap=coverage, match_score=match_score,
        missing_skills=sorted(list(j_sk - r_sk)),
        recommendations=recs, runtime_ms=runtime,
    )
    db.add(m); db.commit(); db.refresh(m)

    return {
        "resume_id": resume.id,
        "job_id": job.id,
        "match_score": round(match_score, 3),
        "semantic_similarity": round(sim, 3),
        "skill_overlap": round(coverage, 3),
        "jd_skills": sorted(list(j_sk)),
        "resume_skills": sorted(list(r_sk)),
        "missing_skills": sorted(list(j_sk - r_sk)),
        "recommendations": recs,
        "runtime_ms": runtime,
        "parsed_metrics": parsed_metrics,
        "improvements": improvements,
    }

