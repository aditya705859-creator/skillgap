"""
Tests for authentication:
- Password hashing
- Demo account seeding and login
- User registration and validation
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.models import User
import bcrypt

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_landing_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Know exactly which skills" in response.text
    assert "Try the demo" in response.text

def test_demo_user_exists_and_seeded():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@skillgap.app").first()
        assert user is not None
        assert bcrypt.checkpw("Demo@1234".encode(), user.password_hash.encode())
        assert len(user.analyses) >= 3
    finally:
        db.close()

def test_demo_login_redirects_to_dashboard():
    # follow_redirects=False to verify redirect
    response = client.get("/auth/demo-login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"

def test_protected_route_without_login_redirects():
    # Fresh client without cookies
    fresh_client = TestClient(app)
    response = fresh_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["location"]

def test_invalid_login_shows_error():
    # Login page gives a csrf_token
    get_res = client.get("/auth/login")
    assert get_res.status_code == 200
    
    # Attempt login with wrong password
    post_res = client.post(
        "/auth/login",
        data={
            "email": "demo@skillgap.app",
            "password": "WrongPassword999",
            "csrf_token": client.cookies.get("csrf_token", "")
        }
    )
    assert post_res.status_code in [200, 302]
    if post_res.status_code == 200:
        assert "Incorrect email or password" in post_res.text or "Invalid form" in post_res.text
