"""
What-if simulator – computes projected score if user learns additional skills.
Uses greedy marginal-gain (score gain per learning hour) for best-next-skill.
"""
from typing import Dict, List

from app.services.scoring import compute_score, _get_grade, WEIGHTS
from app.services.matching import SKILL_RELATIONS


def compute_whatif(
    analysis_results: Dict,
    learn_skills: List[str],
) -> Dict:
    """
    Given the stored analysis results and a list of skills the user would learn,
    compute the projected new score.

    Parameters
    ----------
    analysis_results : the full results_json from the database
    learn_skills     : list of skill names to simulate learning

    Returns a dict with:
      current_score, new_score, new_grade, gained, best_next_skill
    """
    current_score = analysis_results.get("score_breakdown", {}).get("total", 0)
    if not current_score:
        current_score = 0

    matched = list(analysis_results.get("matched_skills", []))
    partial = list(analysis_results.get("partial_skills", []))
    missing = list(analysis_results.get("missing_skills", []))

    # Build sets for fast lookup
    matched_names = {s["name"].lower() for s in matched}
    partial_names = {s["name"].lower(): s for s in partial}

    # Apply learned skills: move from missing/partial to matched
    new_matched = list(matched)
    new_partial = list(partial)
    new_missing = list(missing)

    learn_set = {s.lower() for s in learn_skills}

    for skill_name in learn_skills:
        sk_lower = skill_name.lower()

        # If it was missing, move to matched
        for m in list(new_missing):
            if m["name"].lower() == sk_lower:
                new_matched.append({**m, "confidence": 0.9, "evidence": "Learned skill"})
                new_missing.remove(m)
                break

        # If it was partial, upgrade to full match
        for p in list(new_partial):
            if p["name"].lower() == sk_lower:
                new_matched.append({**p, "confidence": 0.9, "evidence": "Learned skill"})
                new_partial.remove(p)
                break

    total_jd = len(new_matched) + len(new_partial) + len(new_missing)
    if total_jd == 0:
        return {
            "current_score": current_score,
            "new_score": current_score,
            "new_grade": _get_grade(current_score),
            "gained": 0,
            "best_next_skill": None,
        }

    # Recompute score components
    exact_ratio = len(new_matched) / total_jd
    exact_score = exact_ratio * 100 * WEIGHTS["exact_match"]

    total_coverage_sum = len(new_matched) * 1.0 + sum(p.get("similarity", 0.5) for p in new_partial)
    partial_ratio = min(1.0, total_coverage_sum / total_jd)
    partial_score = partial_ratio * 100 * WEIGHTS["partial_match"]

    all_jd = new_matched + new_partial + new_missing
    jd_cats = set(s.get("category", "") for s in all_jd)
    matched_cats = set(s.get("category", "") for s in new_matched + new_partial)
    cat_ratio = len(matched_cats) / max(len(jd_cats), 1)
    cat_score = cat_ratio * 100 * WEIGHTS["category_coverage"]

    # Keep resume quality the same (hasn't changed)
    quality_component = analysis_results.get("score_breakdown", {}).get("resume_quality", 5.0)

    new_total = min(100.0, exact_score + partial_score + cat_score + quality_component)
    new_grade = _get_grade(new_total)

    # Compute best next skill by greedy marginal gain per hour
    best_next = _find_best_next_skill(
        missing=new_missing,
        partial=new_partial,
        current_score=new_total,
        total_jd=total_jd,
        matched=new_matched,
        quality_component=quality_component,
    )

    return {
        "current_score": round(current_score, 1),
        "new_score": round(new_total, 1),
        "new_grade": new_grade,
        "gained": round(new_total - current_score, 1),
        "best_next_skill": best_next,
    }


def _find_best_next_skill(
    missing, partial, current_score, total_jd, matched, quality_component
):
    """Find the skill that gives the most score gain per learning hour."""
    candidates = []

    for skill in missing:
        # Simulate learning this skill
        gain = _score_gain_from_learning(skill, missing, partial, matched, total_jd, quality_component)
        hours = skill.get("learning_hours", 40)
        if hours <= 0:
            hours = 40
        candidates.append({
            "name": skill["name"],
            "gain": round(gain, 1),
            "hours": hours,
            "efficiency": gain / hours,
            "importance": skill.get("importance", "required"),
        })

    # Required skills first, then by gain
    candidates.sort(key=lambda x: (-int(x["importance"] == "required"), -x["gain"]))

    if candidates:
        return candidates[0]
    return None


def _score_gain_from_learning(skill, missing, partial, matched, total_jd, quality_component):
    """Calculate the score gain from learning one additional skill."""
    # New matched count
    new_matched_count = len(matched) + 1
    # Remaining missing (without this skill)
    new_missing_count = len(missing) - 1
    new_partial_count = len(partial)

    exact_ratio = new_matched_count / total_jd
    exact_score = exact_ratio * 100 * WEIGHTS["exact_match"]

    total_coverage_new = new_matched_count * 1.0 + sum(p.get("similarity", 0.5) for p in partial)
    partial_ratio = min(1.0, total_coverage_new / total_jd)
    partial_score = partial_ratio * 100 * WEIGHTS["partial_match"]

    all_jd = matched + partial + missing
    jd_cats = set(s.get("category", "") for s in all_jd)
    new_matched_cats = set(s.get("category", "") for s in matched) | {skill.get("category", "")}
    new_matched_cats |= set(s.get("category", "") for s in partial)
    cat_ratio = len(new_matched_cats) / max(len(jd_cats), 1)
    cat_score = cat_ratio * 100 * WEIGHTS["category_coverage"]

    new_total = min(100.0, exact_score + partial_score + cat_score + quality_component)

    # Current base score
    base_exact = len(matched) / total_jd * 100 * WEIGHTS["exact_match"]
    base_partial = min(1.0, (len(matched) * 1.0 + sum(p.get("similarity", 0.5) for p in partial)) / total_jd) * 100 * WEIGHTS["partial_match"]
    base_cats = set(s.get("category", "") for s in matched + partial)
    base_cat = len(base_cats) / max(len(jd_cats), 1) * 100 * WEIGHTS["category_coverage"]
    base_total = min(100.0, base_exact + base_partial + base_cat + quality_component)

    return max(0.0, new_total - base_total)
