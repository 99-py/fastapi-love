# test/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.mock.todo_data import reset_todo_data

@pytest.fixture()
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def reset_mock_data():
    """每个测试后自动重置模拟数据"""
    # 测试前重置
    reset_todo_data()
    yield
    # 测试后再次重置（可选）
    reset_todo_data()