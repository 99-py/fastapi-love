from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Todo, User
from app.deps import get_current_user

router = APIRouter(prefix="/todos", tags=["todos"])


# 请求体模型
class TodoCreate(BaseModel):
    title: str


# 响应模型（可选）
class TodoResponse(BaseModel):
    id: int
    title: str
    done: bool
    owner_id: int
    shared: bool

    class Config:
        orm_mode = True


@router.post("/", response_model=TodoResponse)
def create_todo(
        todo_data: TodoCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    todo = Todo(
        title=todo_data.title,
        owner_id=user.id,
        shared=True
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@router.get("/", response_model=list[TodoResponse])
def list_my_todos(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    return db.query(Todo).filter(
        Todo.owner_id == user.id
    ).all()

@router.put("/{todo_id}/undo", response_model=TodoResponse)
def mark_todo_undo(
    todo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """取消完成待办事项"""
    todo = db.query(Todo).filter(
        Todo.id == todo_id,
        Todo.owner_id == user.id
    ).first()

    if not todo:
        raise HTTPException(status_code=404, detail="待办事项不存在")

    todo.done = False
    db.commit()
    db.refresh(todo)
    return todo

@router.put("/{todo_id}/done", response_model=TodoResponse)
def mark_todo_done(
        todo_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    todo = db.query(Todo).filter(
        Todo.id == todo_id,
        Todo.owner_id == user.id
    ).first()

    if not todo:
        raise HTTPException(status_code=404, detail="待办事项不存在")

    todo.done = True
    db.commit()
    db.refresh(todo)
    return todo


# 可选：删除待办事项
@router.delete("/{todo_id}")
def delete_todo(
        todo_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    todo = db.query(Todo).filter(
        Todo.id == todo_id,
        Todo.owner_id == user.id
    ).first()

    if not todo:
        raise HTTPException(status_code=404, detail="待办事项不存在")

    db.delete(todo)
    db.commit()
    return {"message": "待办事项已删除"}