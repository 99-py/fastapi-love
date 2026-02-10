from fastapi import APIRouter
from datetime import date

router = APIRouter(prefix="/love", tags=["Love"])

START_DATE = date(2025, 5, 11)  # 自己改

@router.get("/days")
def love_days():
    today = date.today()
    days = (today - START_DATE).days
    return {"days": days}
