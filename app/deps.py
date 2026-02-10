from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from fastapi import Depends


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user
