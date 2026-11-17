"""
Market explorer router.
"""
import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Analysis

router = APIRouter(tags=["market"])


def _ctx(request: Request, **kwargs):
    return request.app.state.template_context(request, **kwargs)


@router.get("/market", response_class=HTMLResponse)
async def market_page(request: Request, db: Session = Depends(get_db)):
    user = request.app.state.get_user(request)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/auth/login", status_code=302)

    # Get user's latest analysis for PCA overlay
    latest = (
        db.query(Analysis)
        .filter(Analysis.user_id == user["id"])
        .order_by(Analysis.created_at.desc())
        .first()
    )

    user_skills = []
    if latest and latest.results_json:
        user_skills = latest.results_json.get("matched_skills", []) + \
                      latest.results_json.get("partial_skills", [])

    from app.services.roles import build_market_chart_data, skill_demand_data, skill_cooccurrence_data
    pca_data = build_market_chart_data(user_skills if user_skills else None)
    demand_data = skill_demand_data()
    cooccurrence_data = skill_cooccurrence_data()

    return request.app.state.templates.TemplateResponse(
        "market.html",
        _ctx(
            request,
            active_page="market",
            pca_data=json.dumps(pca_data),
            demand_data=json.dumps(demand_data),
            cooccurrence_data=json.dumps(cooccurrence_data),
            has_analysis=latest is not None,
        ),
    )
