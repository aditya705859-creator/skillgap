"""
Scoring service – computes the explainable weighted SkillGap score.

Formula (all 100 points):
  60% = exact match ratio  (matched / total_jd_skills)
  20% = partial match ratio (sum of similarity values / total_jd_skills)
  10% = category coverage  (categories with ≥1 match / total jd categories)
  10% = resume quality     (non-zero sections, word count, confidence avg)

Grades: A=90+, B=75-89, C=55-74, D=35-54, F=<35
"""
from typing import Dict, List


GRADE_THRESHOLDS = [
    (90, "A"),
    (75, "B"),
    (55, "C"),
    (35, "D"),
    (0,  "F"),
]

WEIGHTS = {
    "exact_match":        0.60,
    "partial_match":      0.20,
    "category_coverage":  0.10,
    "resume_quality":     0.10,
}


def compute_score(match_result: Dict, resume_skills: List[Dict], sections: Dict) -> Dict:
    """
    Compute the full SkillGap score.

    Parameters
    ----------
    match_result : dict returned by matching.match_skills()
    resume_skills : list of skills extracted from resume
    sections : dict of resume sections (from pdf.extract_pdf_text)

    Returns a dict with all score components and the final score/grade.
    """
    matched = match_result["matched"]
    partial = match_result["partial"]
    missing = match_result["missing"]

    total_jd = len(matched) + len(partial) + len(missing)
    if total_jd == 0:
        return _zero_score("No skills detected in the job description.")

    # 1. Exact match component (0-60)
    exact_ratio = len(matched) / total_jd
    exact_score = exact_ratio * 100 * WEIGHTS["exact_match"]

    # 2. Partial match component (0-20)
    # Exact matches provide 1.0 credit; partial matches provide their similarity credit
    total_coverage_sum = len(matched) * 1.0 + sum(p.get("similarity", 0.5) for p in partial)
    partial_ratio = min(1.0, total_coverage_sum / total_jd)
    partial_score = partial_ratio * 100 * WEIGHTS["partial_match"]

    # 3. Category coverage component (0-10)
    jd_categories = set(
        s["category"] for s in matched + partial + missing
    )
    matched_categories = set(
        s["category"] for s in matched + partial
    )
    if jd_categories:
        cat_ratio = len(matched_categories) / len(jd_categories)
    else:
        cat_ratio = 0.0
    cat_score = cat_ratio * 100 * WEIGHTS["category_coverage"]

    # 4. Resume quality component (0-10)
    quality_score = _resume_quality_score(resume_skills, sections)
    quality_component = quality_score * WEIGHTS["resume_quality"]

    # Total
    total = exact_score + partial_score + cat_score + quality_component
    total = max(0.0, min(100.0, total))

    # Grade
    grade = _get_grade(total)

    # Category-level coverage scores (for radar chart)
    all_jd_skills = matched + partial + missing
    category_scores = _category_scores(all_jd_skills, matched, partial)

    # Verdict
    verdict = _build_verdict(total, grade, len(matched), len(partial), len(missing), total_jd)

    # Next steps
    next_steps = _build_next_steps(missing, partial)

    return {
        "score": round(total, 1),
        "grade": grade,
        "verdict": verdict,
        "next_steps": next_steps,
        "breakdown": {
            "exact_match": round(exact_score, 1),
            "partial_match": round(partial_score, 1),
            "category_coverage": round(cat_score, 1),
            "resume_quality": round(quality_component, 1),
            "total": round(total, 1),
        },
        "counts": {
            "matched": len(matched),
            "partial": len(partial),
            "missing": len(missing),
            "total_jd": total_jd,
        },
        "category_scores": category_scores,
        "low_jd_skill_warning": total_jd < 5,
    }


def _resume_quality_score(resume_skills: List[Dict], sections: Dict) -> float:
    """
    Score resume quality 0-100 based on:
    - Number of sections detected (max 3)
    - Average skill confidence
    - Number of skills found
    """
    populated_sections = sum(
        1 for k, v in sections.items()
        if k not in ("other",) and v.strip()
    )
    section_score = min(populated_sections / 3.0, 1.0)

    if resume_skills:
        avg_conf = sum(s["confidence"] for s in resume_skills) / len(resume_skills)
    else:
        avg_conf = 0.0

    skill_count_score = min(len(resume_skills) / 5.0, 1.0)

    return (section_score * 0.3 + avg_conf * 0.4 + skill_count_score * 0.3) * 100


def _category_scores(all_jd: List[Dict], matched: List[Dict], partial: List[Dict]) -> Dict[str, float]:
    """Return per-category coverage ratio (0.0–1.0)."""
    cats: Dict[str, Dict] = {}
    for s in all_jd:
        cat = s["category"]
        cats.setdefault(cat, {"total": 0, "covered": 0.0})
        cats[cat]["total"] += 1

    for s in matched:
        cat = s["category"]
        if cat in cats:
            cats[cat]["covered"] += 1.0

    for s in partial:
        cat = s["category"]
        if cat in cats:
            cats[cat]["covered"] += s.get("similarity", 0.5)

    return {
        cat: round(vals["covered"] / vals["total"], 2) if vals["total"] else 0.0
        for cat, vals in cats.items()
    }


def _get_grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _zero_score(reason: str) -> Dict:
    return {
        "score": 0.0,
        "grade": "F",
        "verdict": reason,
        "next_steps": [],
        "breakdown": {k: 0.0 for k in WEIGHTS},
        "counts": {"matched": 0, "partial": 0, "missing": 0, "total_jd": 0},
        "category_scores": {},
        "low_jd_skill_warning": True,
    }


def _build_verdict(
    score: float, grade: str, n_matched: int, n_partial: int, n_missing: int, total: int
) -> str:
    pct = int(score)
    if grade == "A":
        return f"Strong match — you cover {n_matched} of {total} required skills and are well positioned for this role."
    elif grade == "B":
        return f"Good match — you cover {n_matched} skills exactly and {n_partial} partially. Closing {min(n_missing, 3)} key gaps would make you competitive."
    elif grade == "C":
        return f"Moderate match at {pct}%. You have solid foundations but are missing {n_missing} skills the role needs."
    elif grade == "D":
        return f"Developing match at {pct}%. Focus on the {min(n_missing, 5)} required skills in the roadmap below."
    else:
        return f"Early stage — {pct}% coverage. Use the roadmap to build the core skills this role requires."


def _build_next_steps(missing: List[Dict], partial: List[Dict]) -> List[str]:
    steps = []
    # Top 2 required missing skills
    required_missing = [s for s in missing if s.get("importance") == "required"][:2]
    for s in required_missing:
        steps.append(f"Learn {s['name']} — a required skill for this role.")
    # Top partial match to complete
    if partial:
        top_partial = sorted(partial, key=lambda x: x.get("similarity", 0))[:1]
        for s in top_partial:
            steps.append(f"Deepen your {s['name']} knowledge (currently partial — {int(s.get('similarity', 0.5)*100)}% credit).")
    if not steps:
        steps.append("Add more detail to your resume to improve skill detection accuracy.")
    return steps[:3]
