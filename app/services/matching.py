"""
Matching service – compares resume skills to JD skills.

Methods:
1. Exact matching: skill found in resume AND jd (case-insensitive name).
2. Partial matching: TF-IDF cosine similarity with character n-grams on skill names
   + a hand-crafted skill-relation map.
3. TF-IDF weighting on the full corpus from jobs.csv.
4. Document-level cosine similarity between resume text and JD text.
"""
import re
import csv
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Partial match threshold: similarity >= this counts as partial
PARTIAL_THRESHOLD = 0.45

# Skill relation map: if user has skill A, it partially covers skill B
# Format: { jd_skill -> (resume_skill, partial_credit_0_to_1) }
SKILL_RELATIONS = {
    "Deep Learning": [("Machine Learning", 0.5), ("Neural Networks", 0.7), ("TensorFlow", 0.6), ("PyTorch", 0.6), ("Keras", 0.65)],
    "Machine Learning": [("scikit-learn", 0.7), ("Statistics", 0.4), ("Python", 0.3)],
    "SQL": [("PostgreSQL", 0.9), ("MySQL", 0.9), ("SQLite", 0.85), ("dbt", 0.6), ("Snowflake", 0.7)],
    "PostgreSQL": [("SQL", 0.8), ("MySQL", 0.75), ("Database Administration", 0.6)],
    "MySQL": [("SQL", 0.8), ("PostgreSQL", 0.75)],
    "TensorFlow": [("Keras", 0.8), ("Deep Learning", 0.6), ("PyTorch", 0.5)],
    "PyTorch": [("TensorFlow", 0.5), ("Deep Learning", 0.65), ("Keras", 0.6)],
    "Kubernetes": [("Docker", 0.6), ("DevOps", 0.4)],
    "Docker": [("Kubernetes", 0.5), ("DevOps", 0.4)],
    "AWS": [("GCP", 0.5), ("Azure", 0.5), ("Cloud Computing", 0.6)],
    "GCP": [("AWS", 0.5), ("Azure", 0.5)],
    "Azure": [("AWS", 0.5), ("GCP", 0.5)],
    "Spark": [("Hadoop", 0.6), ("Big Data", 0.5), ("Python", 0.3)],
    "Kafka": [("Spark", 0.4), ("Big Data", 0.4)],
    "React": [("JavaScript", 0.6), ("TypeScript", 0.55), ("HTML", 0.4)],
    "TypeScript": [("JavaScript", 0.8)],
    "NLP": [("Python", 0.3), ("Machine Learning", 0.4), ("BERT", 0.7), ("Transformers", 0.7)],
    "Computer Vision": [("Deep Learning", 0.5), ("CNNs", 0.7), ("Python", 0.3)],
    "MLOps": [("Docker", 0.5), ("CI/CD", 0.5), ("Kubernetes", 0.4), ("Airflow", 0.4)],
    "CI/CD": [("Git", 0.4), ("Docker", 0.4), ("DevOps", 0.5)],
    "Statistics": [("R", 0.6), ("Python", 0.3), ("MATLAB", 0.5)],
    "A/B Testing": [("Statistics", 0.5), ("Python", 0.3)],
    "Scala": [("Java", 0.5), ("Spark", 0.4)],
    "Airflow": [("Python", 0.3), ("CI/CD", 0.4)],
    "dbt": [("SQL", 0.6), ("Data Wrangling", 0.4)],
    "Snowflake": [("SQL", 0.6), ("Cloud Computing", 0.4)],
    "XGBoost": [("scikit-learn", 0.6), ("Machine Learning", 0.5)],
    "Random Forest": [("scikit-learn", 0.7), ("Machine Learning", 0.5)],
    "Neural Networks": [("Deep Learning", 0.7), ("TensorFlow", 0.6), ("PyTorch", 0.6)],
    "CNNs": [("Deep Learning", 0.7), ("Computer Vision", 0.6)],
    "RNNs": [("Deep Learning", 0.65), ("NLP", 0.5)],
    "Transformers": [("Deep Learning", 0.6), ("NLP", 0.65), ("BERT", 0.8)],
    "LLMs": [("Transformers", 0.7), ("NLP", 0.6), ("Deep Learning", 0.5)],
    "Reinforcement Learning": [("Deep Learning", 0.5), ("Machine Learning", 0.4), ("Python", 0.3)],
    "Time Series": [("Statistics", 0.5), ("Python", 0.4), ("Pandas", 0.4)],
    "Feature Engineering": [("Pandas", 0.5), ("scikit-learn", 0.4), ("Machine Learning", 0.4)],
    "Data Wrangling": [("Pandas", 0.7), ("SQL", 0.5), ("Python", 0.4)],
    "Model Deployment": [("Docker", 0.5), ("FastAPI", 0.5), ("Flask", 0.4)],
    "FastAPI": [("Flask", 0.6), ("Python", 0.4), ("REST APIs", 0.5)],
    "Flask": [("FastAPI", 0.6), ("Python", 0.4), ("REST APIs", 0.5)],
    "Django": [("Flask", 0.5), ("Python", 0.4), ("REST APIs", 0.4)],
}


# ---------------------------------------------------------------------------
# TF-IDF corpus from jobs.csv
# ---------------------------------------------------------------------------
_tfidf_vectorizer: TfidfVectorizer = None
_corpus_matrix = None
_corpus_skills: List[str] = []


def _get_tfidf_vectorizer():
    """Build or return cached TF-IDF vectorizer fitted on job corpus."""
    global _tfidf_vectorizer, _corpus_matrix, _corpus_skills

    if _tfidf_vectorizer is not None:
        return _tfidf_vectorizer

    # Load all skill names + aliases as corpus
    from app.services.nlp import get_registry
    registry = get_registry()

    _corpus_skills = []
    corpus_docs = []
    for row in registry.skills:
        name = row["skill_name"]
        _corpus_skills.append(name)
        # Doc = skill name + its aliases (richer character context)
        aliases = row.get("aliases", "").replace("|", " ")
        corpus_docs.append(f"{name} {aliases}".lower())

    if not corpus_docs:
        return None

    _tfidf_vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        min_df=1,
        max_df=0.95,
    )
    _corpus_matrix = _tfidf_vectorizer.fit_transform(corpus_docs)
    return _tfidf_vectorizer


def _skill_tfidf_similarity(a: str, b: str) -> float:
    """Return TF-IDF character n-gram cosine similarity between two skill name strings."""
    vec = _get_tfidf_vectorizer()
    if vec is None:
        return 0.0
    try:
        vecs = vec.transform([a.lower(), b.lower()])
        sim = cosine_similarity(vecs[0], vecs[1])[0][0]
        return float(sim)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Job-level TF-IDF weighting
# ---------------------------------------------------------------------------
_job_tfidf: TfidfVectorizer = None
_job_skill_weights: Dict[str, float] = {}


def _build_job_weights(jd_text: str) -> Dict[str, float]:
    """
    Fit TF-IDF on jobs.csv corpus + JD, return skill importance weights.
    Rare skills in the corpus but present in JD get higher weight.
    """
    global _job_tfidf

    jobs_csv = DATA_DIR / "jobs.csv"
    if not jobs_csv.exists():
        return {}

    corpus_docs = [jd_text]
    all_skill_names = []
    with open(jobs_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            combined = " ".join([
                row.get("required_skills", "").replace("|", " "),
                row.get("preferred_skills", "").replace("|", " "),
                row.get("description", ""),
            ])
            corpus_docs.append(combined.lower())

    vec = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=1,
        token_pattern=r"[A-Za-z][A-Za-z0-9+#\.\-/_]*",
    )
    try:
        matrix = vec.fit_transform(corpus_docs)
    except Exception:
        return {}

    # Score for the JD (first doc)
    jd_vec = matrix[0]
    feature_names = vec.get_feature_names_out()
    scores = dict(zip(feature_names, jd_vec.toarray()[0]))
    return scores


# ---------------------------------------------------------------------------
# Document-level similarity
# ---------------------------------------------------------------------------
def document_similarity(resume_text: str, jd_text: str) -> float:
    """Cosine similarity between full resume and JD using word TF-IDF."""
    if not resume_text.strip() or not jd_text.strip():
        return 0.0
    vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1)
    try:
        mat = vec.fit_transform([resume_text.lower(), jd_text.lower()])
        sim = cosine_similarity(mat[0], mat[1])[0][0]
        return float(sim)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Main matching function
# ---------------------------------------------------------------------------
def match_skills(
    resume_skills: List[Dict],
    jd_skills: Dict[str, List[Dict]],
    resume_text: str,
    jd_text: str,
) -> Dict:
    """
    Compare resume skills to JD skills.

    Returns a dict with matched, partial, missing lists and metadata.
    """
    resume_names = {s["name"].lower(): s for s in resume_skills}
    jd_all = jd_skills["all"]

    matched = []
    partial = []
    missing = []

    # Build job-level TF-IDF weights
    job_weights = _build_job_weights(jd_text)

    for jd_skill in jd_all:
        jd_name = jd_skill["name"]
        jd_lower = jd_name.lower()

        # 1. Exact match
        if jd_lower in resume_names:
            rs = resume_names[jd_lower]
            # TF-IDF importance weight (default 0.5 if not found)
            importance = job_weights.get(jd_lower, 0.5)
            matched.append({
                **jd_skill,
                "confidence": rs["confidence"],
                "evidence": rs["evidence"],
                "section": rs.get("section", "other"),
                "tfidf_weight": round(importance, 4),
            })
            continue

        # 2. Relation-based partial match
        relation_hit = None
        relations = SKILL_RELATIONS.get(jd_name, [])
        for rel_skill, credit in relations:
            if rel_skill.lower() in resume_names:
                relation_hit = {
                    **jd_skill,
                    "similarity": round(credit, 2),
                    "confidence": resume_names[rel_skill.lower()]["confidence"] * credit,
                    "evidence": resume_names[rel_skill.lower()]["evidence"],
                    "related_to": rel_skill,
                    "match_type": "relation",
                }
                break

        # 3. TF-IDF character n-gram similarity
        tfidf_hit = None
        best_sim = 0.0
        best_rs = None
        for rs_name, rs in resume_names.items():
            sim = _skill_tfidf_similarity(jd_name, rs_name)
            if sim > best_sim:
                best_sim = sim
                best_rs = rs

        if best_sim >= PARTIAL_THRESHOLD:
            tfidf_hit = {
                **jd_skill,
                "similarity": round(best_sim, 2),
                "confidence": round(best_rs["confidence"] * best_sim, 2),
                "evidence": best_rs["evidence"],
                "related_to": best_rs["name"],
                "match_type": "tfidf",
            }

        # Prefer the higher-credit partial match
        if relation_hit and tfidf_hit:
            best_partial = relation_hit if relation_hit["similarity"] >= tfidf_hit["similarity"] else tfidf_hit
        elif relation_hit:
            best_partial = relation_hit
        elif tfidf_hit:
            best_partial = tfidf_hit
        else:
            best_partial = None

        if best_partial:
            partial.append(best_partial)
        else:
            missing.append(jd_skill)

    # Document-level similarity (second signal)
    doc_sim = document_similarity(resume_text, jd_text)

    return {
        "matched": matched,
        "partial": partial,
        "missing": missing,
        "doc_similarity": round(doc_sim, 3),
        "job_weights": job_weights,
    }
