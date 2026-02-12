import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app import models

# 1️⃣ SQLite 引擎
sqlite_engine = create_engine("sqlite:///./todo.db")
SQLiteSession = sessionmaker(bind=sqlite_engine)
sqlite_db = SQLiteSession()

# 2️⃣ PostgreSQL 引擎
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("请设置 DATABASE_URL 为 PostgreSQL 地址")

postgres_engine = create_engine(DATABASE_URL)
PostgresSession = sessionmaker(bind=postgres_engine)
postgres_db = PostgresSession()

print("开始迁移所有表...")

# 遍历所有模型
for table in Base.metadata.sorted_tables:
    table_name = table.name
    model_class = None

    # 找到对应的模型类
    for attr in dir(models):
        obj = getattr(models, attr)
        if hasattr(obj, "__tablename__") and obj.__tablename__ == table_name:
            model_class = obj
            break

    if not model_class:
        continue

    print(f"迁移表: {table_name}")

    rows = sqlite_db.query(model_class).all()

    for row in rows:
        data = {
            column.name: getattr(row, column.name)
            for column in row.__table__.columns
        }
        postgres_db.add(model_class(**data))

    print(f"  -> {len(rows)} 条完成")

postgres_db.commit()

sqlite_db.close()
postgres_db.close()

print("🎉 全部迁移完成")
