from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")
print("当前 DATABASE_URL:", DATABASE_URL)
if not DATABASE_URL:
    # 本地开发
    DATABASE_URL = "sqlite:///./todo.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# FastAPI 依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
