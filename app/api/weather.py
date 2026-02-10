from fastapi import APIRouter
from app.service.weather_service import get_weather

router = APIRouter()

@router.get("/")
def weather(city: str):
    return {"city": city, "weather": get_weather()}
