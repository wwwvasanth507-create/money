from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.api.deps import get_current_user_optional
from app.models.user import User

templates = Jinja2Templates(directory="templates")

router = APIRouter(tags=["Frontend Views"])

@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def index(request: Request, current_user: Optional[User] = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.api_route("/login", methods=["GET", "HEAD"], response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@router.api_route("/register", methods=["GET", "HEAD"], response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@router.api_route("/dashboard", methods=["GET", "HEAD"], response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@router.api_route("/games/crash", methods=["GET", "HEAD"], response_class=HTMLResponse)
def crash_game_page(request: Request):
    return templates.TemplateResponse(request=request, name="games/crash.html")

@router.api_route("/games/mines", methods=["GET", "HEAD"], response_class=HTMLResponse)
def mines_game_page(request: Request):
    return templates.TemplateResponse(request=request, name="games/mines.html")

@router.api_route("/games/dice", methods=["GET", "HEAD"], response_class=HTMLResponse)
def dice_game_page(request: Request):
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.api_route("/wallet", methods=["GET", "HEAD"], response_class=HTMLResponse)
def wallet_page(request: Request):
    return templates.TemplateResponse(request=request, name="wallet.html")

@router.api_route("/kyc", methods=["GET", "HEAD"], response_class=HTMLResponse)
def kyc_page(request: Request):
    return templates.TemplateResponse(request=request, name="kyc.html")

@router.api_route("/admin/verification-desk", methods=["GET", "HEAD"], response_class=HTMLResponse)
def verification_desk_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin/verification_desk.html")

@router.api_route("/admin/dashboard", methods=["GET", "HEAD"], response_class=HTMLResponse)
def admin_dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin/dashboard.html")
