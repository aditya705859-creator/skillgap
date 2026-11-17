"""
Account router – settings, change password, delete account.
"""
import bcrypt
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Analysis

router = APIRouter(prefix="/account", tags=["account"])


def _ctx(request: Request, **kwargs):
    return request.app.state.template_context(request, **kwargs)


def _flash(request: Request, cat: str, msg: str):
    request.app.state.flash(request, cat, msg)


@router.get("", response_class=HTMLResponse)
async def account_page(request: Request):
    user = request.app.state.get_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=302)
    return request.app.state.templates.TemplateResponse(
        "account.html",
        _ctx(request, active_page="account"),
    )


@router.post("/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    user_session = request.app.state.get_user(request)
    if not user_session:
        return RedirectResponse("/auth/login", status_code=302)

    if not request.app.state.verify_csrf_token(request, csrf_token):
        _flash(request, "error", "Invalid form submission.")
        return RedirectResponse("/account", status_code=302)

    errors = []
    if len(new_password) < 8:
        errors.append("New password must be at least 8 characters.")
    if new_password != new_password_confirm:
        errors.append("New passwords do not match.")

    if not errors:
        user = db.query(User).filter(User.id == user_session["id"]).first()
        if not user or not bcrypt.checkpw(current_password.encode(), user.password_hash.encode()):
            errors.append("Current password is incorrect.")

    if errors:
        return request.app.state.templates.TemplateResponse(
            "account.html",
            _ctx(request, active_page="account", pw_errors=errors),
        )

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    user.password_hash = new_hash
    db.commit()

    _flash(request, "success", "Password updated successfully.")
    return RedirectResponse("/account", status_code=302)


@router.post("/delete", response_class=HTMLResponse)
async def delete_account(
    request: Request,
    confirm_delete: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    user_session = request.app.state.get_user(request)
    if not user_session:
        return RedirectResponse("/auth/login", status_code=302)

    if not request.app.state.verify_csrf_token(request, csrf_token):
        _flash(request, "error", "Invalid form submission.")
        return RedirectResponse("/account", status_code=302)

    if confirm_delete.lower() != "delete":
        _flash(request, "error", "Please type 'delete' to confirm account deletion.")
        return RedirectResponse("/account", status_code=302)

    user = db.query(User).filter(User.id == user_session["id"]).first()
    if user:
        db.delete(user)
        db.commit()

    request.session.clear()
    return RedirectResponse("/?deleted=1", status_code=302)
