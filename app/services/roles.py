"""
Role-fit service – ranks job roles by cosine similarity to user's skill profile.
Uses jobs.csv skill vectors and PCA + KMeans for the market chart.
"""
import csv
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_jobs() -> List[Dict]:
    jobs_csv = DATA_DIR / "jobs.csv"
    if not jobs_csv.exists():
        return []
    with open(jobs_csv, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_skills() -> List[str]:
    skills_csv = DATA_DIR / "skills.csv"
    if not skills_csv.exists():
        return []
    with open(skills_csv, newline="", encoding="utf-8") as f:
        return [row["skill_name"] for row in csv.DictReader(f)]


def build_role_vectors(
    all_skill_names: List[str],
) -> Tuple[np.ndarray, List[str], List[Dict]]:
    """
    Build a binary skill-presence matrix for each job role.

    Returns:
      matrix: shape (n_roles, n_skills) with 1.0 for required, 0.5 for preferred
      role_names: list of role name strings
      jobs: raw job dicts
    """
    jobs = _load_jobs()
    if not all_skill_names or not jobs:
        return np.zeros((0, 0)), [], []

    skill_index = {s.lower(): i for i, s in enumerate(all_skill_names)}
    matrix = np.zeros((len(jobs), len(all_skill_names)))

    for j_idx, job in enumerate(jobs):
        for skill in job.get("required_skills", "").split("|"):
            skill = skill.strip()
            idx = skill_index.get(skill.lower())
            if idx is not None:
                matrix[j_idx, idx] = 1.0
        for skill in job.get("preferred_skills", "").split("|"):
            skill = skill.strip()
            idx = skill_index.get(skill.lower())
            if idx is not None:
                matrix[j_idx, idx] = max(matrix[j_idx, idx], 0.5)

    role_names = [j["role"] for j in jobs]
    return matrix, role_names, jobs


def rank_roles(resume_skills: List[Dict]) -> List[Dict]:
    """
    Rank all job roles by cosine similarity to the resume's skill vector.

    Returns top-10 matches with score, description, etc.
    """
    all_skill_names = _load_skills()
    if not all_skill_names:
        return []

    matrix, role_names, jobs = build_role_vectors(all_skill_names)
    if matrix.shape[0] == 0:
        return []

    # Build user skill vector
    skill_index = {s.lower(): i for i, s in enumerate(all_skill_names)}
    user_vec = np.zeros(len(all_skill_names))
    for s in resume_skills:
        idx = skill_index.get(s["name"].lower())
        if idx is not None:
            user_vec[idx] = s["confidence"]

    if user_vec.sum() == 0:
        return []

    # Cosine similarity
    user_norm = normalize(user_vec.reshape(1, -1))
    job_norm = normalize(matrix)
    sims = cosine_similarity(user_norm, job_norm)[0]

    ranked = []
    for idx, sim in enumerate(sims):
        job = jobs[idx]
        ranked.append({
            "role": role_names[idx],
            "score": round(float(sim) * 100, 1),
            "description": job.get("description", ""),
            "avg_salary_usd": int(job.get("avg_salary_usd", 0)),
            "category": job.get("category", ""),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:10]


def build_market_chart_data(user_resume_skills: Optional[List[Dict]] = None) -> Dict:
    """
    PCA + KMeans clustering of all job roles for the market explorer page.

    Returns data needed to draw the scatter chart:
      - x, y: 2D PCA coordinates
      - roles: list of role names
      - clusters: cluster labels
      - user_x, user_y: user position (if resume_skills provided)
    """
    all_skill_names = _load_skills()
    if not all_skill_names:
        return {}

    matrix, role_names, jobs = build_role_vectors(all_skill_names)
    if matrix.shape[0] < 3:
        return {}

    # PCA to 2D
    n_components = min(2, matrix.shape[0] - 1, matrix.shape[1])
    pca = PCA(n_components=n_components)
    coords = pca.fit_transform(matrix)

    # KMeans clustering
    n_clusters = min(5, len(role_names))
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = km.fit_predict(matrix).tolist()

    result = {
        "x": coords[:, 0].tolist(),
        "y": coords[:, 1].tolist() if coords.shape[1] > 1 else [0.0] * len(role_names),
        "roles": role_names,
        "clusters": cluster_labels,
        "user_x": None,
        "user_y": None,
        "explained_variance": [round(v, 3) for v in pca.explained_variance_ratio_.tolist()],
        "categories": [j.get("category", "") for j in jobs],
        "salaries": [int(j.get("avg_salary_usd", 0)) for j in jobs],
    }

    # Project user onto same PCA space
    if user_resume_skills:
        skill_index = {s.lower(): i for i, s in enumerate(all_skill_names)}
        user_vec = np.zeros(len(all_skill_names))
        for s in user_resume_skills:
            idx = skill_index.get(s["name"].lower())
            if idx is not None:
                user_vec[idx] = s["confidence"]
        user_coords = pca.transform(user_vec.reshape(1, -1))[0]
        result["user_x"] = float(user_coords[0])
        result["user_y"] = float(user_coords[1]) if len(user_coords) > 1 else 0.0

    return result


def skill_demand_data() -> Dict:
    """
    Compute skill demand from jobs.csv (how many roles require each skill).
    Returns data for a bar chart.
    """
    jobs = _load_jobs()
    if not jobs:
        return {"skills": [], "counts": []}

    demand: Dict[str, int] = {}
    for job in jobs:
        for skill in job.get("required_skills", "").split("|"):
            skill = skill.strip()
            if skill:
                demand[skill] = demand.get(skill, 0) + 1

    # Sort by demand
    sorted_demand = sorted(demand.items(), key=lambda x: x[1], reverse=True)
    top_30 = sorted_demand[:30]
    return {
        "skills": [s for s, _ in top_30],
        "counts": [c for _, c in top_30],
    }


def skill_cooccurrence_data() -> Dict:
    """
    Compute skill co-occurrence matrix for the heatmap.
    Returns top-15 skills by demand and their co-occurrence counts.
    """
    jobs = _load_jobs()
    if not jobs:
        return {"skills": [], "matrix": []}

    # First get top 15 skills by demand
    demand: Dict[str, int] = {}
    for job in jobs:
        for skill in job.get("required_skills", "").split("|"):
            s = skill.strip()
            if s:
                demand[s] = demand.get(s, 0) + 1

    top_skills = [s for s, _ in sorted(demand.items(), key=lambda x: x[1], reverse=True)[:15]]
    skill_idx = {s: i for i, s in enumerate(top_skills)}
    n = len(top_skills)
    matrix = [[0] * n for _ in range(n)]

    for job in jobs:
        skills_in_role = set()
        for sk in job.get("required_skills", "").split("|"):
            s = sk.strip()
            if s in skill_idx:
                skills_in_role.add(s)
        # Count co-occurrence
        skills_list = list(skills_in_role)
        for i in range(len(skills_list)):
            for j in range(len(skills_list)):
                if i != j:
                    a, b = skill_idx[skills_list[i]], skill_idx[skills_list[j]]
                    matrix[a][b] += 1

    return {"skills": top_skills, "matrix": matrix}
