from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_and_list_todo():
    # 创建 todo
    resp = client.post("/todos/", json={"title": "陪她散步"})
    assert resp.status_code == 200

    data = resp.json()
    assert data["title"] == "陪她散步"
    assert data["done"] is False

    # 查询 todo
    resp = client.get("/todos/")
    todos = resp.json()

    assert len(todos) == 1
    assert todos[0]["title"] == "陪她散步"
