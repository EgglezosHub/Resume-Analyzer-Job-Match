# app/routes/auth.py
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from authlib.integrations.starlette_client import OAuth

from app.db.session import SessionLocal
from app.db.models import User
from app.core.config import settings as cfg

from app.utils.passwords import hash_password, verify_password
from starlette.templating import Jinja2Templates


router = APIRouter(prefix="", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


# DB dep
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Email + Password ----------
@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup", response_class=HTMLResponse)
async def signup_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = (email or "").strip().lower()
    pwd = (password or "").strip()

    err = None
    if not email or "@" not in email:
        err = "Please enter a valid email."
    elif len(pwd) < 8:
        err = "Password must be at least 8 characters."
    elif db.query(User).filter(User.email == email).first():
        err = "An account with this email already exists."

    if err:
        return templates.TemplateResponse("signup.html", {"request": request, "error": err, "email": email})

    u = User(email=email, name=email.split("@")[0], password_hash=hash_password(pwd))
    db.add(u); db.commit(); db.refresh(u)

    if hasattr(request, "session"):
        request.session["user_id"] = u.id

    return RedirectResponse(url="/dashboard", status_code=302)

@router.get("/login/password", response_class=HTMLResponse)
async def login_password_page(request: Request):
    return templates.TemplateResponse("login_password.html", {"request": request})

@router.post("/login/password", response_class=HTMLResponse)
async def login_password_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = (email or "").strip().lower()
    pwd = (password or "").strip()

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash or not verify_password(pwd, user.password_hash):
        return templates.TemplateResponse(
            "login_password.html",
            {"request": request, "error": "Invalid email or password.", "email": email},
        )

    if hasattr(request, "session"):
        request.session["user_id"] = user.id

    return RedirectResponse(url="/dashboard", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    if hasattr(request, "session"):
        request.session.clear()
    return RedirectResponse(url="/", status_code=302)


# ----- OAuth (GitHub = OAuth2, NOT OIDC) -----
oauth = OAuth()
if cfg.github_client_id and cfg.github_client_secret:
    oauth.register(
        name="github",
        client_id=cfg.github_client_id,
        client_secret=cfg.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )

def _abs(request: Request, path: str) -> str:
    return f"{request.url.scheme}://{request.url.netloc}{path}"

@router.get("/login/github")
async def login_github(request: Request):
    if "github" not in oauth._clients:
        # GitHub creds not configured; just go home.
        return RedirectResponse("/")
    redirect_uri = _abs(request, "/auth/github/callback")
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/auth/github/callback")
async def auth_github_callback(request: Request, db: Session = Depends(get_db)):
    if "github" not in oauth._clients:
        return RedirectResponse("/?error=github_not_configured")

    token = await oauth.github.authorize_access_token(request)
    # Basic user info
    me = await oauth.github.get("user", token=token)
    data = me.json() if me else {}
    email = data.get("email")
    # Some accounts don’t return email in /user unless public; fetch primary email
    if not email:
        emails = await oauth.github.get("user/emails", token=token)
        if emails and emails.json():
            prim = next((e for e in emails.json() if e.get("primary")), None)
            email = (prim or emails.json()[0]).get("email")

    if not email:
        return RedirectResponse("/?error=no_email_from_github")

    # Upsert user
    user: Optional[User] = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=data.get("name") or data.get("login"))
        db.add(user); db.commit(); db.refresh(user)

    # Put into session
    if hasattr(request, "session"):
        request.session["user_id"] = user.id
        request.session["user_email"] = user.email
        request.session["user_name"] = user.name or ""

    # Go to dashboard
    return RedirectResponse("/dashboard")

@router.get("/logout")
async def logout(request: Request):
    if hasattr(request, "session"):
        request.session.clear()
    return RedirectResponse("/")

