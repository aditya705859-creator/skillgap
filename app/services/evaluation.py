"""
Evaluation module – runs hand-labelled test cases and returns precision/recall/F1.
Used by the About page to show honest, computed numbers.
"""
from pathlib import Path
from typing import Dict, List


# ---------------------------------------------------------------------------
# Hand-labelled test cases
# These are the ground-truth cases for skill extraction evaluation.
# Format: { "text": str, "expected": [str, ...] }
# ---------------------------------------------------------------------------
TEST_CASES = [
    {
        "id": "tc01",
        "description": "Should NOT match Excel in 'excellent'",
        "text": "I am an excellent communicator with strong interpersonal skills.",
        "expected_skills": [],
        "should_not_match": ["Excel"],
    },
    {
        "id": "tc02",
        "description": "Should NOT match Java inside JavaScript",
        "text": "Proficient in JavaScript, React, and Node.js development.",
        "expected_skills": ["JavaScript", "React", "Node.js"],
        "should_not_match": ["Java"],
    },
    {
        "id": "tc03",
        "description": "Should NOT match Git inside 'digital'",
        "text": "Experience in digital marketing and content strategy.",
        "expected_skills": [],
        "should_not_match": ["Git"],
    },
    {
        "id": "tc04",
        "description": "Should NOT match ML inside HTML",
        "text": "Built websites using HTML, CSS, and JavaScript.",
        "expected_skills": ["HTML", "CSS", "JavaScript"],
        "should_not_match": ["Machine Learning"],
    },
    {
        "id": "tc05",
        "description": "Should NOT match R as standalone in 'R&D' or 'for'",
        "text": "Led R&D initiatives and worked across teams for data collection.",
        "expected_skills": [],
        "should_not_match": ["R"],
    },
    {
        "id": "tc06",
        "description": "Match C++ correctly",
        "text": "Developed high-performance systems using C++ and CUDA.",
        "expected_skills": ["C++"],
        "should_not_match": [],
    },
    {
        "id": "tc07",
        "description": "Match scikit-learn correctly",
        "text": "Trained ML models using scikit-learn, pandas, and numpy.",
        "expected_skills": ["scikit-learn", "Pandas", "NumPy"],
        "should_not_match": [],
    },
    {
        "id": "tc08",
        "description": "Match CI/CD correctly",
        "text": "Set up CI/CD pipelines using GitHub Actions and Docker.",
        "expected_skills": ["CI/CD", "Docker"],
        "should_not_match": [],
    },
    {
        "id": "tc09",
        "description": "Full data science resume extraction",
        "text": (
            "Skills: Python, SQL, TensorFlow, PyTorch. "
            "Experience: Built deep learning models using TensorFlow for NLP tasks. "
            "Used AWS for model deployment. Familiar with Docker and Kubernetes."
        ),
        "expected_skills": ["Python", "SQL", "TensorFlow", "PyTorch", "AWS", "Docker", "Kubernetes"],
        "should_not_match": [],
    },
    {
        "id": "tc10",
        "description": "Match Node.js and distinguish from plain JS",
        "text": "Built REST APIs using Node.js and Express. Frontend in React.",
        "expected_skills": ["Node.js", "React", "REST APIs"],
        "should_not_match": [],
    },
]


def run_evaluation() -> Dict:
    """
    Run all test cases and compute precision, recall, F1.

    Returns:
      { "results": [...], "precision": float, "recall": float, "f1": float, "total": int }
    """
    from app.services.nlp import get_registry, extract_skills_from_resume

    registry = get_registry()
    case_results = []

    total_tp = 0
    total_fp = 0
    total_fn = 0

    for tc in TEST_CASES:
        text = tc["text"]
        # Create minimal sections dict
        sections = {
            "skills": text if "Skills:" in text else "",
            "experience": text if "Experience:" in text else "",
            "projects": "",
            "education": "",
            "summary": "",
            "other": text,
        }
        extracted = extract_skills_from_resume(sections, text)
        extracted_names = [s["name"].lower() for s in extracted]

        expected = [s.lower() for s in tc.get("expected_skills", [])]
        should_not = [s.lower() for s in tc.get("should_not_match", [])]

        # True positives: expected skills that were found
        tp = [s for s in expected if s in extracted_names]
        # False negatives: expected skills NOT found
        fn = [s for s in expected if s not in extracted_names]
        # False positives from should_not_match list
        fp_forbidden = [s for s in should_not if s in extracted_names]
        # False positives from unexpected extracted (not in expected, if expected is non-empty)
        fp_unexpected = [s for s in extracted_names if s not in expected and expected] if expected else []

        # Combine all FPs
        fp = list(set(fp_forbidden + fp_unexpected))

        total_tp += len(tp)
        total_fp += len(fp)
        total_fn += len(fn)

        passed = len(fp_forbidden) == 0 and len(fn) == 0
        case_results.append({
            "id": tc["id"],
            "description": tc["description"],
            "text_preview": tc["text"][:100] + "..." if len(tc["text"]) > 100 else tc["text"],
            "expected": tc.get("expected_skills", []),
            "should_not_match": tc.get("should_not_match", []),
            "extracted": [s["name"] for s in extracted],
            "true_positives": [s.capitalize() if len(s) <= 2 else s for s in tp],
            "false_positives": fp,
            "false_negatives": [s for s in tc.get("expected_skills", []) if s.lower() in fn],
            "passed": passed,
        })

    # Compute overall metrics
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    passed_count = sum(1 for r in case_results if r["passed"])

    return {
        "results": case_results,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "total": len(TEST_CASES),
        "passed": passed_count,
        "note": (
            f"Evaluated on {len(TEST_CASES)} hand-labelled test cases. "
            f"{passed_count} passed completely. "
            "This is a small sample; results on unseen resumes may differ."
        ),
    }


def get_evaluation_results() -> Dict:
    """Get evaluation results, with graceful error handling."""
    try:
        return run_evaluation()
    except Exception as e:
        return {
            "results": [],
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "total": 0,
            "passed": 0,
            "note": f"Evaluation could not run: {e}",
        }
