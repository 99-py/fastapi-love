from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models import Moment
from app.db import SessionLocal
from app.service.todo_service import list_todos
from app.service.weather_service import get_weather
from app.service.greeting_service import generate_greeting
from datetime import datetime,date
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.templates import templates
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    username = request.session.get("username")

    if not user_id:
        return RedirectResponse("/login")

    todos = list_todos(db, user_id)

    weather = None
    greeting = None
    times = datetime.now().hour
    if username == "her":
        weather = get_weather()
        greeting = generate_greeting(weather,times)
    if username == "her":
        role = "her"
    else:
        role = "me"
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page": "home",
            "role": role,
            "todos": todos,
            "username": username,
            "greeting": greeting,
        }
    )
@router.get("/album", response_class=HTMLResponse)
def album(request: Request):
    return templates.TemplateResponse(
        "album.html",
        {
            "request": request,
            "page": "album",
            "role": request.session.get("username"),
        }
    )
# @router.get("/memory", response_class=HTMLResponse)
# def memory(request: Request):
#     return templates.TemplateResponse(
#         "memory.html",
#         {
#             "request": request,
#             "page": "memory",
#             "role": request.session.get("username"),
#         }
#     )
@router.get("/timeline", response_class=HTMLResponse)
def timeline(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse("/login")

    moments = db.query(Moment).order_by(Moment.created_at.desc()).all()

    return templates.TemplateResponse(
        "timeline.html",
        {
            "request": request,
            "moments": moments
        }
    )