from app.service.greeting_service import generate_greeting

def test_generate_greeting_morning_sunny():
    text = generate_greeting(days=10, weather="sunny", hour=9)
    assert "早安" in text
    assert "第 10 天" in text
    assert "阳光" in text
def test_greeting_api(client):
    resp = client.get("/greeting", params={"user_id": 1, "city": "Beijing"})
    assert resp.status_code == 200
    assert "greeting" in resp.json()
