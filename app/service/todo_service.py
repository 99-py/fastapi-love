from sqlalchemy.orm import Session
from app.models import Todo, Couple

def create_todo(db: Session, owner_id: int, title: str, shared: bool = True):
    todo = Todo(
        owner_id=owner_id,
        title=title,
        shared=shared,
        done=False
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo

def list_todos(db: Session, user_id: int):
    couple = db.query(Couple).filter(
        (Couple.user1_id == user_id) |
        (Couple.user2_id == user_id)
    ).first()

    if not couple:
        return []

    partner_id = (
        couple.user2_id if couple.user1_id == user_id
        else couple.user1_id
    )

    return db.query(Todo).filter(
        (Todo.owner_id == user_id) |
        ((Todo.owner_id == partner_id) & (Todo.shared == True))
    ).all()
