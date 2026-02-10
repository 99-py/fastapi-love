def test_add_todo(client):
    resp = client.post(
        "/todos/",
        json={"title": "一起去旅行"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "一起去旅行"
    assert data["done"] is False


def test_list_todos(client):
    # 先创建一些测试数据
    client.post("/todos/", json={"title": "测试待办1"})
    client.post("/todos/", json={"title": "测试待办2"})

    # 然后查询
    resp = client.get("/todos/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2  # 现在至少有2条
    # 你可以进一步验证数据内容

def test_finish_todo(client):
    create_resp = client.post("/todos/", json={"title": "待完成的待办"})
    todo_id = create_resp.json()["id"]

    # 然后完成它
    resp = client.put(f"/todos/{todo_id}/done")
    assert resp.status_code == 200
    assert resp.json()["done"] is True
