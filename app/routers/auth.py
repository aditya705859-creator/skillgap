"""
Auth router – sign up, log in, log out.
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import bcrypt

from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _templates(request: Request):
    return request.app.state.templates


def _ctx(request: Request, **kwargs):
    return request.app.state.template_context(request, **kwargs)


def _flash(request: Request, cat: str, msg: str):
    request.app.state.flash(request, cat, msg)


# ---------------------------------------------------------------------------
# Sign up
# ---------------------------------------------------------------------------
@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    user = request.app.state.get_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return _templates(request).TemplateResponse("auth/signup.html", _ctx(request))


@router.post("/signup", response_class=HTMLResponse)
async def signup_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    tmpl = _templates(request)
    errors = []
    
    # CSRF check
    if not request.app.state.verify_csrf_token(request, csrf_token):
        errors.append("Invalid form submission. Please try again.")
    
    # Validation
    name = name.strip()
    email = email.strip().lower()
    
    if not name or len(name) < 2:
        errors.append("Name must be at least 2 characters.")
    if not email or "@" not in email or "." not in email:
        errors.append("Please enter a valid email address.")
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if password != password_confirm:
        errors.append("Passwords do not match.")
    
    # Check existing user
    if not errors:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            errors.append("An account with this email already exists.")
    
    if errors:
        return tmpl.TemplateResponse(
            "auth/signup.html",
            _ctx(request, errors=errors, form_name=name, form_email=email),
        )
    
    # Create user
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(name=name, email=email, password_hash=pw_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log in immediately
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_email"] = user.email
    
    _flash(request, "success", f"Welcome to SkillGap, {user.name}!")
    return RedirectResponse(url="/dashboard", status_code=302)


# ---------------------------------------------------------------------------
# Log in
# ---------------------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = request.app.state.get_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return _templates(request).TemplateResponse("auth/login.html", _ctx(request))


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    tmpl = _templates(request)
    
    if not request.app.state.verify_csrf_token(request, csrf_token):
        return tmpl.TemplateResponse(
            "auth/login.html",
            _ctx(request, errors=["Invalid form submission. Please try again."], form_email=email),
        )
    
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return tmpl.TemplateResponse(
            "auth/login.html",
            _ctx(request, errors=["Incorrect email or password."], form_email=email),
        )
    
    # Set session
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_email"] = user.email
    
    _flash(request, "success", f"Welcome back, {user.name}!")
    return RedirectResponse(url="/dashboard", status_code=302)


# ---------------------------------------------------------------------------
# Demo login
# ---------------------------------------------------------------------------
@router.get("/demo-login")
async def demo_login(request: Request, db: Session = Depends(get_db)):
    """Log in as the demo user."""
    user = db.query(User).filter(User.email == "demo@skillgap.app").first()
    if not user:
        _flash(request, "error", "Demo account not available.")
        return RedirectResponse(url="/", status_code=302)
    
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_email"] = user.email
    
    _flash(request, "success", "Logged in as demo user. Explore freely!")
    return RedirectResponse(url="/dashboard", status_code=302)


# ---------------------------------------------------------------------------
# Log out
# ---------------------------------------------------------------------------
@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form("")):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
