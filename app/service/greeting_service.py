def generate_greeting(weather: dict | None, hour: int) -> str:
    # 时间段
    if hour < 11:
        time_text = "早安"
    elif hour < 18:
        time_text = "下午好"
    else:
        time_text = "晚安"

    # 天气文案
    if weather:
        temp = weather["temp"]
        text = weather["text"]

        if temp <= 15:
            weather_text = f"今天咸阳有点冷{temp}°{text}，注意保暖呀"
        elif temp >= 30:
            weather_text = f"今天咸阳挺热的{temp}°{text}，注意防暑"
        else:
            weather_text = f"咸阳今天{temp}°{text}，气温宜人，可以出来走走，散散步"
    else:
        weather_text = "我没查到天气，但我还是很想你"

    return f"{time_text} ❤️ {weather_text}"
