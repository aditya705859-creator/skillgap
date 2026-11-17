"""
Career assistant – rule-based Q&A over stored analysis results.
No external API calls.
"""
from typing import Dict, List, Optional
import re


SUGGESTED_QUESTIONS = [
    "What should I learn first?",
    "Why is my score low?",
    "Which role fits me best?",
    "How long will it take to close my gaps?",
    "What are my strongest skills?",
    "Which skills are most in demand?",
]

# ---------------------------------------------------------------------------
# Pattern-answer rules
# ---------------------------------------------------------------------------

def _build_rules(results: Dict) -> List[Dict]:
    """
    Build a list of (pattern, answer_fn) rules from the analysis results.
    Rules are tried in order; first match wins.
    """
    score = results.get("score_breakdown", {}).get("total", 0)
    grade = results.get("grade", "F")
    matched = results.get("matched_skills", [])
    partial = results.get("partial_skills", [])
    missing = results.get("missing_skills", [])
    roadmap = results.get("roadmap", [])
    top_roles = results.get("top_roles", [])
    verdict = results.get("verdict", "")

    # Pre-compute useful values
    n_matched = len(matched)
    n_partial = len(partial)
    n_missing = len(missing)
    n_total = n_matched + n_partial + n_missing

    required_missing = [s for s in missing if s.get("importance") == "required"]
    preferred_missing = [s for s in missing if s.get("importance") == "preferred"]

    top_matched = sorted(matched, key=lambda x: x.get("confidence", 0), reverse=True)[:5]
    top_matched_names = [s["name"] for s in top_matched]

    first_roadmap = roadmap[0] if roadmap else None
    best_role = top_roles[0] if top_roles else None

    rules = [
        # Score / grade questions
        {
            "patterns": [r"why.*score\s+low", r"score.*low", r"bad\s+score", r"low.*grade"],
            "answer": lambda: (
                f"Your score is {score:.0f}% (grade {grade}). "
                + (f"You are missing {n_missing} skills the job requires, including: "
                   f"{', '.join(s['name'] for s in required_missing[:3])}. "
                   if required_missing else "")
                + "Focus on the required missing skills to improve your score the fastest."
            ),
        },
        {
            "patterns": [r"what.*score", r"my score", r"score.*mean", r"what.*grade"],
            "answer": lambda: (
                f"Your score is {score:.0f} out of 100 (grade {grade}). "
                f"You matched {n_matched} of {n_total} skills exactly, with {n_partial} partial matches "
                f"and {n_missing} missing. {verdict}"
            ),
        },

        # What to learn first
        {
            "patterns": [r"learn\s+first", r"start.*learn", r"what.*learn", r"next\s+step", r"priority"],
            "answer": lambda: (
                f"Start with <b>{first_roadmap['skill']}</b> "
                f"(estimated {first_roadmap['hours']} hours, {first_roadmap['difficulty']} level). "
                + (f"You can practice it with the project: <i>{first_roadmap['project_name']}</i>." if first_roadmap.get("project_name") else "")
                if first_roadmap else
                "Great news — your skills already closely match what this role needs. Focus on deepening your partial matches."
            ),
        },

        # Strongest skills
        {
            "patterns": [r"strong.*skill", r"best.*skill", r"good.*at", r"strengths?"],
            "answer": lambda: (
                f"Your strongest matched skills are: {', '.join(top_matched_names)}. "
                f"These were detected with high confidence and appear prominently in your resume."
                if top_matched_names else
                "No strong skill matches were found. Try uploading a more detailed resume."
            ),
        },

        # Role fit
        {
            "patterns": [r"which\s+role", r"best\s+role", r"role.*fit", r"what\s+job", r"what.*career"],
            "answer": lambda: (
                f"Your strongest role match is <b>{best_role['role']}</b> ({best_role['score']:.0f}% fit). "
                + (f"The next best matches are: {', '.join(r['role'] for r in top_roles[1:4])}."
                   if len(top_roles) > 1 else "")
                if best_role else
                "Role matching requires more skills to be detected. Upload a detailed resume."
            ),
        },

        # Time to close gaps
        {
            "patterns": [r"how long", r"time\s+to", r"how\s+much\s+time", r"hours"],
            "answer": lambda: (
                f"Your roadmap includes {len(roadmap)} skills to learn. "
                f"The total estimated learning time is {sum(s.get('hours', 0) for s in roadmap)} hours. "
                f"Focusing on the top 3 required skills takes about "
                f"{sum(s.get('hours', 0) for s in roadmap[:3])} hours."
                if roadmap else
                "You have no major gaps to fill. Focus on deepening existing skills."
            ),
        },

        # Partial matches
        {
            "patterns": [r"partial", r"almost", r"close\s+to"],
            "answer": lambda: (
                f"You have {n_partial} partially matched skills. "
                + (f"The closest are: "
                   + ", ".join(
                       f"{s['name']} ({int(s.get('similarity', 0.5)*100)}% credit)"
                       for s in sorted(partial, key=lambda x: x.get("similarity", 0), reverse=True)[:3]
                   ) + ". Deepening these is often quicker than learning new skills from scratch."
                   if partial else "")
            ),
        },

        # Missing skills
        {
            "patterns": [r"miss.*skill", r"lack.*skill", r"what.*need", r"skill.*gap"],
            "answer": lambda: (
                f"You are missing {n_missing} skills. "
                + (f"Required: {', '.join(s['name'] for s in required_missing[:5])}. " if required_missing else "")
                + (f"Preferred: {', '.join(s['name'] for s in preferred_missing[:3])}." if preferred_missing else "")
                if missing else
                "No missing skills detected — your resume closely matches the job description!"
            ),
        },

        # Demand / market
        {
            "patterns": [r"in\s+demand", r"market", r"popular.*skill", r"trending"],
            "answer": lambda: (
                "The most in-demand skills across roles are Python, SQL, Machine Learning, Docker, and Cloud platforms (AWS/GCP/Azure). "
                "Check the Job Market page for a full demand breakdown and skill co-occurrence chart."
            ),
        },

        # Fallback
        {
            "patterns": [r".*"],
            "answer": lambda: (
                f"Your current score is {score:.0f}% for grade {grade}. "
                f"You have {n_matched} matched skills, {n_partial} partial matches, and {n_missing} gaps. "
                "Try asking: 'What should I learn first?', 'Why is my score low?', or 'Which role fits me best?'"
            ),
        },
    ]

    return rules


def answer_question(question: str, analysis_results: Dict) -> str:
    """
    Answer a career assistant question using rule-based matching.

    Parameters
    ----------
    question : user's natural language question
    analysis_results : full results_json from the database

    Returns the answer as an HTML-safe string.
    """
    if not analysis_results:
        return (
            "I don't have analysis results to reference yet. "
            "Complete an analysis first, then come back to ask questions."
        )

    rules = _build_rules(analysis_results)
    q_lower = question.lower().strip()

    for rule in rules:
        for pattern in rule["patterns"]:
            if re.search(pattern, q_lower):
                try:
                    return rule["answer"]()
                except Exception:
                    continue

    return (
        "I am not sure how to answer that. Try asking about your score, missing skills, "
        "what to learn first, or which role fits you best."
    )
