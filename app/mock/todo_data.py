from typing import List
from app.schema.todo import TodoOut

# 模拟数据库里的自增 ID
_fake_id = 1

# 模拟数据库表
_fake_todos: List[TodoOut] = []

def reset_todo_data():
    """重置模拟数据，用于测试"""
    global _fake_id, _fake_todos
    _fake_id = 1
    _fake_todos.clear()
def get_all_todos() -> List[TodoOut]:
    return _fake_todos


def create_todo(title: str) -> TodoOut:
    global _fake_id

    todo = TodoOut(
        id=_fake_id,
        title=title,
        done=False
    )
    _fake_todos.append(todo)
    _fake_id += 1
    return todo


def mark_done(todo_id: int) -> TodoOut | None:
    for todo in _fake_todos:
        if todo.id == todo_id:
            todo.done = True
            return todo
    return None
