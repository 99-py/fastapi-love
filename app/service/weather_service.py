# app/services/weather_service.py
import requests

WEATHER_CODE_MAP = {
    0: "晴天",
    1: "多云",
    2: "多云",
    3: "阴天",
    45: "有雾",
    48: "有雾",
    51: "小雨",
    61: "下雨",
    71: "下雪",
    80: "阵雨",
}

def get_weather() -> dict | None:
    """
    返回示例：
    {
        "temp": 23,
        "text": "多云"
    }
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=34.3296"
        "&longitude=108.7093"
        "&current_weather=true"
    )

    try:
        res = requests.get(url, timeout=3)
        data = res.json()

        current = data.get("current_weather")
        if not current:
            return None

        temp = int(current["temperature"])
        code = current["weathercode"]
        text = WEATHER_CODE_MAP.get(code, "天气不错")

        return {
            "temp": temp,
            "text": text
        }

    except Exception as e:
        print("Weather API error:", e)
        return None
