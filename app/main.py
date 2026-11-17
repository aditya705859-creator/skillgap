"""
SkillGap – main FastAPI application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env before anything else
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.db import init_db, SessionLocal
from app.seed import seed_demo_user
from app.routers import auth, analyses, market, assistant, account

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="SkillGap", docs_url=None, redoc_url=None)

# Session middleware for cookie-based auth
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production-123456")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=86400 * 7)

# Static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 templates with version compatibility wrapper
class CompatJinja2Templates(Jinja2Templates):
    """Allows both TemplateResponse(name, context) and TemplateResponse(request=..., name=...)."""
    def TemplateResponse(self, *args, **kwargs):
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            name = args[0]
            context = args[1]
            request = kwargs.pop("request", context.get("request"))
            return super().TemplateResponse(request=request, name=name, context=context, **kwargs)
        return super().TemplateResponse(*args, **kwargs)

templates = CompatJinja2Templates(directory=str(TEMPLATES_DIR))

# Initialise database and seed demo data on module import
init_db()
seed_demo_user()

# Upload directory
UPLOAD_DIR = BASE_DIR.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Template context helpers
# ---------------------------------------------------------------------------
def get_user(request: Request):
    """Get user dict from session, or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return {
        "id": user_id,
        "name": request.session.get("user_name", ""),
        "email": request.session.get("user_email", ""),
    }


def generate_csrf_token(request: Request) -> str:
    """Generate or retrieve CSRF token from session."""
    import hashlib, secrets
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_hex(32)
        request.session["csrf_token"] = token
    return token


def verify_csrf_token(request: Request, token: str) -> bool:
    """Verify the submitted CSRF token matches the session."""
    return token == request.session.get("csrf_token")


def flash(request: Request, category: str, message: str):
    """Add a flash message to the session."""
    msgs = request.session.get("flash_messages", [])
    msgs.append([category, message])
    request.session["flash_messages"] = msgs


def get_flashed_messages(request: Request):
    """Pop all flash messages from session."""
    msgs = request.session.pop("flash_messages", [])
    return msgs


def template_context(request: Request, **kwargs):
    """Build the standard template context."""
    ctx = {
        "request": request,
        "user": get_user(request),
        "csrf_token": generate_csrf_token(request),
        "messages": get_flashed_messages(request),
        "active_page": kwargs.pop("active_page", ""),
    }
    ctx.update(kwargs)
    return ctx


# Make helpers importable
app.state.templates = templates
app.state.get_user = get_user
app.state.template_context = template_context
app.state.flash = flash
app.state.verify_csrf_token = verify_csrf_token
app.state.generate_csrf_token = generate_csrf_token
app.state.upload_dir = UPLOAD_DIR


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(analyses.router)
app.include_router(market.router)
app.include_router(assistant.router)
app.include_router(account.router)


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Public landing page."""
    user = get_user(request)
    if user:
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("landing.html", template_context(request))


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About and methodology page."""
    from app.services.evaluation import get_evaluation_results
    eval_results = get_evaluation_results()
    return templates.TemplateResponse(
        "about.html",
        template_context(request, active_page="about", eval_results=eval_results),
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment."""
    return {"status": "ok", "app": "SkillGap"}


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        "error.html",
        template_context(request, error_code=404, error_message="Page not found",
                         error_detail="The page you are looking for does not exist or has been moved."),
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse(
        "error.html",
        template_context(request, error_code=500, error_message="Something went wrong",
                         error_detail="We hit an unexpected error. Please try again or contact support."),
        status_code=500,
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialise database and seed demo data."""
    init_db()
    seed_demo_user()
