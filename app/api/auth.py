from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.core.templates import templates
from app.models import User
from app.service.weather_service import get_weather
from app.service.greeting_service import generate_greeting
from fastapi.responses import HTMLResponse
router = APIRouter()

from fastapi.responses import RedirectResponse

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """显示登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})
@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.name == username).first()
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "用户不存在"
            }
        )

    request.session["user_id"] = user.id
    request.session["username"] = user.name

    return RedirectResponse(url="/", status_code=302)

    # ⭐ 如果是她，返回天气问候
    if user.name == "her":
        weather = get_weather()
        if weather:
            greeting = generate_greeting(
                weather["temp"],
                weather["text"]
            )
            result["weather"] = weather
            result["greeting"] = greeting

    return result


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"msg": "已退出登录"}
