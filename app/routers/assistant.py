"""
Career assistant router.
"""
import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Analysis
from app.services.assistant import SUGGESTED_QUESTIONS

router = APIRouter(tags=["assistant"])


def _ctx(request: Request, **kwargs):
    return request.app.state.template_context(request, **kwargs)


@router.get("/assistant", response_class=HTMLResponse)
async def assistant_page(request: Request, db: Session = Depends(get_db)):
    user = request.app.state.get_user(request)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/auth/login", status_code=302)

    latest = (
        db.query(Analysis)
        .filter(Analysis.user_id == user["id"])
        .order_by(Analysis.created_at.desc())
        .first()
    )

    return request.app.state.templates.TemplateResponse(
        "assistant.html",
        _ctx(
            request,
            active_page="assistant",
            analysis=latest,
            suggested_questions=SUGGESTED_QUESTIONS,
        ),
    )


@router.post("/api/assistant")
async def assistant_api(request: Request, db: Session = Depends(get_db)):
    user = request.app.state.get_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    body = await request.json()
    question = body.get("question", "").strip()
    analysis_id = body.get("analysis_id")

    if not question:
        return JSONResponse({"answer": "Please ask a question."})

    # Find analysis
    if analysis_id:
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id,
            Analysis.user_id == user["id"],
        ).first()
    else:
        analysis = (
            db.query(Analysis)
            .filter(Analysis.user_id == user["id"])
            .order_by(Analysis.created_at.desc())
            .first()
        )

    results = analysis.results_json if analysis else {}

    from app.services.assistant import answer_question
    answer = answer_question(question, results)
    return JSONResponse({"answer": answer})
