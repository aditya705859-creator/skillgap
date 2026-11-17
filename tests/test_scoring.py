"""
Tests for scoring, role ranking, roadmap, and what-if calculations.
Verifies that known input gives known output.
"""
import pytest
from app.services.scoring import compute_score, _get_grade, WEIGHTS
from app.services.roadmap import build_roadmap
from app.services.whatif import compute_whatif

def test_weights_sum_to_one():
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 1e-6

def test_grades():
    assert _get_grade(95) == "A"
    assert _get_grade(90) == "A"
    assert _get_grade(89.9) == "B"
    assert _get_grade(75) == "B"
    assert _get_grade(74.9) == "C"
    assert _get_grade(55) == "C"
    assert _get_grade(54.9) == "D"
    assert _get_grade(35) == "D"
    assert _get_grade(34.9) == "F"
    assert _get_grade(0) == "F"

def test_perfect_score_gives_a():
    # 5 skills, all matched exactly across multiple categories
    matched = [
        {"name": "Python", "category": "Programming", "confidence": 1.0, "evidence": "Expert"},
        {"name": "SQL", "category": "Database", "confidence": 1.0, "evidence": "Expert"},
        {"name": "Pandas", "category": "Data Science", "confidence": 1.0, "evidence": "Expert"},
        {"name": "Docker", "category": "DevOps", "confidence": 1.0, "evidence": "Expert"},
        {"name": "AWS", "category": "Cloud", "confidence": 1.0, "evidence": "Expert"},
    ]
    sections = {"skills": "Python, SQL", "experience": "Docker", "projects": "Pandas", "education": "AWS"}
    match_result = {
        "matched": matched,
        "partial": [],
        "missing": [],
        "doc_similarity": 0.95
    }
    resume_skills = matched
    res = compute_score(match_result, resume_skills, sections)
    
    assert res["score"] >= 90
    assert res["grade"] == "A"
    assert res["counts"]["matched"] == 5
    assert res["counts"]["missing"] == 0

def test_zero_matches_gives_f():
    missing = [
        {"name": "Python", "category": "Programming", "importance": "required"},
        {"name": "SQL", "category": "Database", "importance": "required"},
    ]
    sections = {"skills": "", "experience": "", "projects": "", "education": "", "other": ""}
    match_result = {
        "matched": [],
        "partial": [],
        "missing": missing,
        "doc_similarity": 0.0
    }
    res = compute_score(match_result, [], sections)
    assert res["score"] < 35
    assert res["grade"] == "F"

def test_partial_match_credit():
    matched = [{"name": "Python", "category": "Programming", "confidence": 1.0, "evidence": "Python"}]
    partial = [{"name": "Deep Learning", "category": "Deep Learning", "similarity": 0.7, "confidence": 0.7, "evidence": "ML"}]
    missing = [{"name": "Docker", "category": "DevOps", "importance": "required"}]
    sections = {"skills": "Python", "experience": "ML", "projects": "", "education": ""}
    
    match_result = {
        "matched": matched,
        "partial": partial,
        "missing": missing,
        "doc_similarity": 0.5
    }
    res = compute_score(match_result, matched, sections)
    
    assert res["breakdown"]["exact_match"] > 0
    assert res["breakdown"]["partial_match"] > 0
    assert res["breakdown"]["category_coverage"] > 0
    assert res["counts"]["total_jd"] == 3

def test_roadmap_topological_order():
    # If a skill has prerequisites in the list, prereqs should come first
    missing = [
        {"name": "TensorFlow", "category": "Deep Learning", "importance": "required"},
        {"name": "Python", "category": "Programming", "importance": "required"},
    ]
    roadmap = build_roadmap(missing, [])
    skill_order = [item["skill"] for item in roadmap]
    if "Python" in skill_order and "TensorFlow" in skill_order:
        assert skill_order.index("Python") < skill_order.index("TensorFlow")

def test_whatif_simulator_score_increase():
    analysis_results = {
        "score_breakdown": {
            "exact_match": 20.0,
            "partial_match": 0.0,
            "category_coverage": 5.0,
            "resume_quality": 5.0,
            "total": 30.0
        },
        "matched_skills": [{"name": "Python", "category": "Programming"}],
        "partial_skills": [],
        "missing_skills": [
            {"name": "SQL", "category": "Database", "importance": "required", "learning_hours": 20},
            {"name": "Docker", "category": "DevOps", "importance": "required", "learning_hours": 30}
        ]
    }
    
    res = compute_whatif(analysis_results, ["SQL"])
    assert res["new_score"] > res["current_score"]
    assert res["gained"] > 0
    assert res["best_next_skill"] is not None
