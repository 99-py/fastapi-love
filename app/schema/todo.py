from pydantic import BaseModel
from typing import List,Optional


# 创建 Todo 时的输入
class TodoCreate(BaseModel):

    title: str
    done: Optional[bool] = False


# 更新 Todo 时的输入
class TodoUpdate(BaseModel):
    user_id: int
    title: str
    done: bool


# 返回给前端的 Todo 结构
class TodoOut(BaseModel):
    id: int
    title: str
    done: bool
