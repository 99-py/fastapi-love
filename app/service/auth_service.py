from sqlalchemy.orm import Session
from app.models import User

def login(db: Session, username: str):
    return db.query(User).filter(User.name == username).first()
