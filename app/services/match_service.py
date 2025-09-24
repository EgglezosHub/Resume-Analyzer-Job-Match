# app/services/match_service.py
from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.db.models import Resume, Job  # type hints only
from app.nlp.embeddings import embed
from app.nlp.skills_extractor import extract_skills
from app.utils.timing import timer


def _cosine(u, v) -> float:
    if u is None or v is None:
        return 0.0
    # handle zero vectors
    up = sum(x * x for x in u) ** 0.5
    vp = sum(x * x for x in v) ** 0.5
    if up == 0.0 or vp == 0.0:
        return 0.0
    dot = sum(x * y for x, y in zip(u, v))
    return max(0.0, min(1.0, dot / (up * vp)))


def _recommendations(missing: List[str], jd_skills: List[str], coverage: float) -> List[str]:
    tips: List[str] = []
    if missing:
        top = ", ".join(missing[:8]) + ("…" if len(missing) > 8 else "")
        tips.append(f"Show experience with: {top} (projects, bullets, or links).")

    jd_text = " ".join(jd_skills).lower()
    cloudish = any(k in jd_text for k in ["aws", "gcp", "azure", "cloud", "terraform", "iac", "kubernetes"])
    frameworks = any(k in jd_text for k in ["spring", "django", "fastapi", "react", "vue", "next", "nestjs"])

    if coverage < 1.0 and (cloudish or frameworks):
        tips.append(
            "Add a tiny public sample for the missing stack (e.g., a 3–5 file API or IaC snippet) and link it."
        )
    if coverage < 0.6:
        tips.append("Tighten keywords in your summary/skills section to match the JD phrasing more directly.")
    return tips


def match_resume_job(db: Session, resume: Resume, job: Job) -> dict:
    """
    Pure function: compute similarity + skill overlap and suggested actions.
    (No DB writes; persistence happens when creating the Report.)
    """
    with timer() as elapsed:
        r_text = resume.text or ""
        j_text = job.description or ""

        # Embeddings similarity
        r_vec = embed(r_text)
        j_vec = embed(j_text)
        semantic_similarity = _cosine(r_vec, j_vec)

        # Skills overlap
        jd_skills = sorted(set(extract_skills(j_text)))
        resume_skills = sorted(set(extract_skills(r_text)))

        jd_set = set(jd_skills)
        res_set = set(resume_skills)
        overlap = sorted(list(jd_set & res_set))
        missing = sorted(list(jd_set - res_set))

        skill_overlap = (len(overlap) / len(jd_skills)) if jd_skills else 0.0

        # Blended score (tweak weights if you want)
        match_score = round(0.6 * semantic_similarity + 0.4 * skill_overlap, 4)

        # Recommendations
        recs = _recommendations(missing, jd_skills, skill_overlap)

        runtime_ms = int(elapsed())

    return {
        "jd_skills": jd_skills,
        "resume_skills": resume_skills,
        "overlap_skills": overlap,
        "missing_skills": missing,
        "semantic_similarity": float(semantic_similarity),
        "skill_overlap": float(skill_overlap),
        "match_score": float(match_score),
        "recommendations": recs,
        "runtime_ms": runtime_ms,
    }

