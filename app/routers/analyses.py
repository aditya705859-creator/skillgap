"""
Analyses router – new analysis, results, dashboard, what-if, report download.
"""
import os
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Analysis, User

router = APIRouter(tags=["analyses"])

SAMPLE_JD = """We are looking for a Data Scientist to join our team.

Required:
- Python programming
- Machine Learning and statistical modelling
- SQL for data querying
- Experience with scikit-learn, pandas, and numpy
- A/B testing and experimental design
- Data visualization (Tableau or Plotly)
- Git version control

Nice to have:
- Deep Learning with TensorFlow or PyTorch
- Cloud experience (AWS or GCP)
- Spark for large-scale data processing
- Docker for containerisation
"""


def _require_login(request: Request):
    """Return user dict or raise redirect."""
    user = request.app.state.get_user(request)
    if not user:
        return None
    return user


def _ctx(request: Request, **kwargs):
    return request.app.state.template_context(request, **kwargs)


def _flash(request: Request, cat: str, msg: str):
    request.app.state.flash(request, cat, msg)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user["id"])
        .order_by(Analysis.created_at.desc())
        .limit(20)
        .all()
    )

    chronological = list(reversed(analyses))
    latest_a = analyses[0] if analyses else None
    earliest_a = chronological[0] if chronological else None

    # Handle duplicate dates by appending run index
    date_counts = {}
    for a in chronological:
        d_str = a.created_at.strftime("%d %b")
        date_counts[d_str] = date_counts.get(d_str, 0) + 1

    seen_counts = {}
    display_labels = []
    for a in chronological:
        d_str = a.created_at.strftime("%d %b")
        if date_counts[d_str] > 1:
            seen_counts[d_str] = seen_counts.get(d_str, 0) + 1
            display_labels.append(f"{d_str} (#{seen_counts[d_str]})")
        else:
            display_labels.append(d_str)

    trend_data = {
        "dates": display_labels,
        "raw_dates": [a.created_at.strftime("%d %b %Y, %H:%M") for a in chronological],
        "scores": [round(a.score or 0, 1) for a in chronological],
        "roles": [a.target_role or "Analysis" for a in chronological],
        "grades": [a.grade or "F" for a in chronological],
        "ids": [a.id for a in chronological],
    }

    latest_score = round(latest_a.score or 0, 1) if latest_a else 0
    latest_grade = latest_a.grade or "F" if latest_a else "F"
    latest_role = latest_a.target_role or "Role" if latest_a else ""
    earliest_score = round(earliest_a.score or 0, 1) if earliest_a else 0
    score_change = round(latest_score - earliest_score, 1) if len(analyses) > 1 else None
    best_score = round(max((a.score or 0) for a in analyses), 1) if analyses else 0
    avg_score = round(sum((a.score or 0) for a in analyses) / len(analyses), 1) if analyses else 0

    return request.app.state.templates.TemplateResponse(
        "dashboard.html",
        _ctx(
            request,
            active_page="dashboard",
            analyses=analyses,
            trend_data=json.dumps(trend_data),
            latest_score=latest_score,
            latest_grade=latest_grade,
            latest_role=latest_role,
            score_change=score_change,
            best_score=best_score,
            avg_score=avg_score,
        ),
    )


# ---------------------------------------------------------------------------
# New analysis – Step 1 & 2
# ---------------------------------------------------------------------------
@router.get("/analysis/new", response_class=HTMLResponse)
async def new_analysis_page(request: Request):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    return request.app.state.templates.TemplateResponse(
        "analysis/new.html",
        _ctx(request, active_page="new_analysis", sample_jd=SAMPLE_JD),
    )


@router.post("/analysis/new", response_class=HTMLResponse)
async def new_analysis_submit(
    request: Request,
    resume_file: UploadFile = File(...),
    jd_text: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    tmpl = request.app.state.templates
    errors = []

    # CSRF check
    if not request.app.state.verify_csrf_token(request, csrf_token):
        errors.append("Invalid form submission. Please try again.")

    # Validate JD
    jd_text = jd_text.strip()
    if len(jd_text) < 50:
        errors.append("Job description is too short. Please paste the full JD (at least 50 characters).")

    # Validate file
    if not resume_file.filename:
        errors.append("Please upload your resume as a PDF file.")
    elif not resume_file.filename.lower().endswith(".pdf"):
        errors.append("Only PDF files are accepted.")

    if errors:
        return tmpl.TemplateResponse(
            "analysis/new.html",
            _ctx(request, active_page="new_analysis", errors=errors,
                 sample_jd=SAMPLE_JD, form_jd=jd_text),
        )

    # Read PDF
    file_bytes = await resume_file.read()
    if len(file_bytes) == 0:
        errors.append("The uploaded file is empty.")
    elif len(file_bytes) > 10 * 1024 * 1024:
        errors.append("File is too large. Maximum size is 10 MB.")

    if errors:
        return tmpl.TemplateResponse(
            "analysis/new.html",
            _ctx(request, active_page="new_analysis", errors=errors,
                 sample_jd=SAMPLE_JD, form_jd=jd_text),
        )

    # Extract PDF text
    from app.services.pdf import extract_pdf_text
    pdf_result = extract_pdf_text(file_bytes)

    if pdf_result.get("error"):
        return tmpl.TemplateResponse(
            "analysis/new.html",
            _ctx(request, active_page="new_analysis",
                 errors=[pdf_result["error"]], sample_jd=SAMPLE_JD, form_jd=jd_text),
        )

    resume_text = pdf_result["text"]

    # Run NLP pipeline
    from app.services.nlp import extract_skills_from_resume, extract_skills_from_jd
    from app.services.matching import match_skills
    from app.services.scoring import compute_score
    from app.services.roles import rank_roles
    from app.services.roadmap import build_roadmap

    sections = pdf_result["sections"]
    resume_skills = extract_skills_from_resume(sections, resume_text)
    jd_skills = extract_skills_from_jd(jd_text)
    match_result = match_skills(resume_skills, jd_skills, resume_text, jd_text)
    score_result = compute_score(match_result, resume_skills, sections)
    top_roles = rank_roles(resume_skills)
    roadmap = build_roadmap(match_result["missing"], match_result["partial"])

    # Detect target role (top matching role)
    target_role = top_roles[0]["role"] if top_roles else "Role not detected"

    # Build results_json
    results_json = {
        "matched_skills": match_result["matched"],
        "partial_skills": match_result["partial"],
        "missing_skills": match_result["missing"],
        "score_breakdown": score_result["breakdown"],
        "verdict": score_result["verdict"],
        "next_steps": score_result["next_steps"],
        "counts": score_result["counts"],
        "category_scores": score_result["category_scores"],
        "top_roles": top_roles,
        "roadmap": roadmap,
        "doc_similarity": match_result.get("doc_similarity", 0),
        "jd_skill_count": len(jd_skills["all"]),
        "resume_word_count": pdf_result["word_count"],
        "page_count": pdf_result["page_count"],
        "low_jd_skill_warning": score_result.get("low_jd_skill_warning", False),
    }

    # Save to database
    analysis = Analysis(
        user_id=user["id"],
        target_role=target_role,
        resume_filename=resume_file.filename,
        resume_text=resume_text[:5000],  # store first 5k chars
        jd_text=jd_text[:3000],
        results_json=results_json,
        score=score_result["score"],
        grade=score_result["grade"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return RedirectResponse(f"/analysis/{analysis.id}", status_code=302)


# ---------------------------------------------------------------------------
# Results page
# ---------------------------------------------------------------------------
@router.get("/analysis/{analysis_id}", response_class=HTMLResponse)
async def analysis_results(
    request: Request,
    analysis_id: int,
    db: Session = Depends(get_db),
):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user["id"],
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    results = analysis.results_json or {}

    return request.app.state.templates.TemplateResponse(
        "analysis/results.html",
        _ctx(
            request,
            active_page="dashboard",
            analysis=analysis,
            results=results,
            results_json=json.dumps(results),
        ),
    )


# ---------------------------------------------------------------------------
# Delete analysis
# ---------------------------------------------------------------------------
@router.post("/analysis/{analysis_id}/delete")
async def delete_analysis(
    request: Request,
    analysis_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user["id"],
    ).first()

    if analysis:
        db.delete(analysis)
        db.commit()
        _flash(request, "success", "Analysis deleted.")

    return RedirectResponse("/dashboard", status_code=302)


# ---------------------------------------------------------------------------
# What-if API endpoint
# ---------------------------------------------------------------------------
@router.post("/api/whatif")
async def whatif_api(request: Request, db: Session = Depends(get_db)):
    user = _require_login(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    body = await request.json()
    analysis_id = body.get("analysis_id")
    learn_skills = body.get("learn_skills", [])

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user["id"],
    ).first()

    if not analysis:
        return JSONResponse({"error": "Not found"}, status_code=404)

    from app.services.whatif import compute_whatif
    result = compute_whatif(analysis.results_json or {}, learn_skills)
    return JSONResponse(result)


# ---------------------------------------------------------------------------
# PDF report download
# ---------------------------------------------------------------------------
@router.get("/analysis/{analysis_id}/report")
async def download_report(
    request: Request,
    analysis_id: int,
    db: Session = Depends(get_db),
):
    user = _require_login(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user["id"],
    ).first()

    if not analysis:
        raise HTTPException(status_code=404)

    from app.services.report import generate_pdf_report
    pdf_bytes = generate_pdf_report(analysis, user["name"])

    filename = f"skillgap_report_{analysis.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
