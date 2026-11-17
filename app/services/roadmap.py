"""
Roadmap service – prerequisite-ordered learning plan using networkx.
"""
import csv
import re
import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_skills_map() -> Dict[str, Dict]:
    skills_csv = DATA_DIR / "skills.csv"
    skills_map = {}
    if not skills_csv.exists():
        return skills_map
    with open(skills_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            skills_map[row["skill_name"]] = row
    return skills_map


def _load_projects() -> List[Dict]:
    projects_csv = DATA_DIR / "projects.csv"
    if not projects_csv.exists():
        return []
    with open(projects_csv, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _find_project_for_skill(skill_name: str, projects: List[Dict]) -> Optional[Dict]:
    """Find the best project for practising a given skill."""
    skill_lower = skill_name.lower()
    for project in projects:
        practiced = [s.strip().lower() for s in project.get("skills_practiced", "").split("|")]
        if skill_lower in practiced:
            return project
    # Fallback: partial match
    for project in projects:
        practiced = [s.strip().lower() for s in project.get("skills_practiced", "").split("|")]
        if any(skill_lower in p or p in skill_lower for p in practiced):
            return project
    return None


def build_roadmap(missing_skills: List[Dict], partial_skills: List[Dict]) -> List[Dict]:
    """
    Build a topologically sorted learning roadmap for missing (and partial) skills.

    Uses networkx to respect prerequisites and sort from foundations to advanced.
    Returns a list of dicts with skill info, suggested project, and order.
    """
    skills_map = _load_skills_map()
    projects = _load_projects()

    # Combine missing + low-partial skills
    skills_to_learn = list(missing_skills)
    for s in partial_skills:
        if s.get("similarity", 1.0) < 0.6:
            skills_to_learn.append(s)

    if not skills_to_learn:
        return []

    # Build directed prerequisite graph
    G = nx.DiGraph()
    target_skill_names = {s["name"] for s in skills_to_learn}

    for skill in skills_to_learn:
        name = skill["name"]
        G.add_node(name)
        # Get prerequisites from skills_map
        row = skills_map.get(name, {})
        prereqs = [p.strip() for p in re.split(r"[,|]", row.get("prerequisites", "")) if p.strip()]
        for prereq in prereqs:
            if prereq in target_skill_names:
                G.add_edge(prereq, name)  # prereq must come before name

    # Topological sort (prerequisites first)
    try:
        ordered = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        # Cycle fallback: use original order
        ordered = [s["name"] for s in skills_to_learn]

    # Build roadmap items
    roadmap = []
    seen = set()
    for skill_name in ordered:
        if skill_name in seen:
            continue
        seen.add(skill_name)

        # Find skill data
        skill_data = next((s for s in skills_to_learn if s["name"] == skill_name), None)
        if not skill_data:
            continue

        row = skills_map.get(skill_name, {})
        project = _find_project_for_skill(skill_name, projects)

        roadmap.append({
            "skill": skill_name,
            "category": skill_data.get("category", row.get("category", "Other")),
            "difficulty": row.get("difficulty", skill_data.get("difficulty", "Intermediate")),
            "hours": int(row.get("learning_hours", skill_data.get("learning_hours", 40))),
            "importance": skill_data.get("importance", "required"),
            "prerequisites": [p.strip() for p in re.split(r"[,|]", row.get("prerequisites", "")) if p.strip()],
            "project_name": project["project_name"] if project else None,
            "project_hours": int(project.get("estimated_hours", 10)) if project else None,
            "project_url": project.get("resource_url", "") if project else None,
            "project_description": project.get("description", "") if project else None,
            "is_partial": skill_data.get("match_type") is not None,
        })

    return roadmap
