"""
Tests for NLP skill extraction:
- Boundary traps: Excel vs excellent, Java vs JavaScript, Git vs digital, ML vs HTML, R in R&D
- Special symbols: C++, C#, Node.js, CI/CD, scikit-learn
- Confidence and section weighting
"""
import pytest
from app.services.nlp import extract_skills_from_resume, extract_skills_from_jd, get_registry

def test_registry_loaded():
    reg = get_registry()
    assert len(reg.skills) >= 80
    assert len(reg.patterns) >= 80

def test_no_false_positive_excel_in_excellent():
    text = "She has excellent verbal communication and organization capabilities."
    sections = {"skills": "", "experience": text, "projects": "", "education": "", "other": ""}
    skills = extract_skills_from_resume(sections, text)
    names = [s["name"] for s in skills]
    assert "Excel" not in names

def test_no_false_positive_java_in_javascript():
    text = "Engineered frontend interactive web components using JavaScript and Vue."
    sections = {"skills": "", "experience": text, "projects": "", "education": "", "other": ""}
    skills = extract_skills_from_resume(sections, text)
    names = [s["name"] for s in skills]
    assert "JavaScript" in names
    assert "Java" not in names

def test_no_false_positive_git_in_digital():
    text = "Managed digital media initiatives and advertising programs."
    sections = {"skills": "", "experience": text, "projects": "", "education": "", "other": ""}
    skills = extract_skills_from_resume(sections, text)
    names = [s["name"] for s in skills]
    assert "Git" not in names

def test_no_false_positive_ml_in_html():
    text = "Created HTML web pages and style templates."
    sections = {"skills": "", "experience": text, "projects": "", "education": "", "other": ""}
    skills = extract_skills_from_resume(sections, text)
    names = [s["name"] for s in skills]
    assert "HTML" in names
    assert "Machine Learning" not in names

def test_no_false_positive_r_in_rd():
    text = "Directed technical R&D team on internal research programs for company."
    sections = {"skills": "", "experience": text, "projects": "", "education": "", "other": ""}
    skills = extract_skills_from_resume(sections, text)
    names = [s["name"] for s in skills]
    assert "R" not in names

def test_extract_cpp_and_csharp():
    text = "Built backend microservices using C++ and C# with .NET core."
    sections = {"skills": "", "experience": text, "projects": "", "education": "", "other": ""}
    skills = extract_skills_from_resume(sections, text)
    names = [s["name"] for s in skills]
    assert "C++" in names
    assert "C#" in names

def test_extract_nodejs_and_cicd():
    text = "Implemented Node.js backend services and configured CI/CD workflows."
    sections = {"skills": text, "experience": "", "projects": "", "education": "", "other": ""}
    skills = extract_skills_from_resume(sections, text)
    names = [s["name"].lower() for s in skills]
    assert "node.js" in names
    assert "ci/cd" in names

def test_extract_scikit_learn():
    text = "Trained classification models with scikit-learn and pandas."
    sections = {"skills": "", "experience": "", "projects": text, "education": "", "other": ""}
    skills = extract_skills_from_resume(sections, text)
    names = [s["name"].lower() for s in skills]
    assert "scikit-learn" in names
    assert "pandas" in names

def test_section_confidence_weighting():
    skill_text = "Proficient in Python."
    exp_text = "Maintained software using Python."
    sec_skills = {"skills": skill_text, "experience": "", "projects": "", "education": "", "other": ""}
    sec_exp = {"skills": "", "experience": exp_text, "projects": "", "education": "", "other": ""}
    
    res1 = extract_skills_from_resume(sec_skills, skill_text)
    res2 = extract_skills_from_resume(sec_exp, exp_text)
    
    assert res1[0]["confidence"] > res2[0]["confidence"]
    assert len(res1[0]["evidence"]) > 0

def test_jd_required_vs_preferred():
    jd = "Must have Python and SQL. Preferred: Docker and Kubernetes."
    extracted = extract_skills_from_jd(jd)
    req_names = [s["name"] for s in extracted["required"]]
    pref_names = [s["name"] for s in extracted["preferred"]]
    
    assert "Python" in req_names
    assert "SQL" in req_names
    assert "Docker" in pref_names or "Kubernetes" in pref_names
