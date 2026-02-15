import os
from sqlalchemy import create_engine, text
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

    # 清空目标表（如果已存在数据）
    try:
        postgres_db.execute(text(f'DELETE FROM "{table_name}"'))
        print(f"  -> 已清空目标表 {table_name}")
    except Exception as e:
        print(f"  -> 清空表 {table_name} 时出错: {e}")
        postgres_db.rollback()
        continue

    rows = sqlite_db.query(model_class).all()

    for row in rows:
        # 获取所有列数据
        data = {}
        for column in row.__table__.columns:
            column_name = column.name
            value = getattr(row, column_name)

            # 如果是主键ID列，且数据库有自增序列，可以不指定ID
            # 但为了保持数据完整性，我们仍然保留ID
            data[column_name] = value

        # 创建新对象
        new_obj = model_class(**data)
        postgres_db.add(new_obj)

    print(f"  -> {len(rows)} 条记录迁移完成")

postgres_db.commit()

print("\n🚀 数据迁移完成，开始修复序列...")

# 修复所有表的序列
tables_to_fix = []
for table in Base.metadata.sorted_tables:
    tables_to_fix.append(table.name)

print(f"需要修复序列的表: {tables_to_fix}")

for table_name in tables_to_fix:
    try:
        # 检查是否有自增序列
        check_seq_sql = """
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = :table_name 
            AND column_name = 'id'
            AND column_default LIKE 'nextval%'
        )
        """

        result = postgres_db.execute(text(check_seq_sql), {"table_name": table_name})
        has_sequence = result.scalar()

        if has_sequence:
            # 获取当前最大ID
            max_id_result = postgres_db.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}"'))
            max_id = max_id_result.scalar()

            if max_id > 0:
                # 重置序列
                seq_name = f"{table_name}_id_seq"
                reset_sql = f"SELECT setval('{seq_name}', :max_id + 1, false)"
                postgres_db.execute(text(reset_sql), {"max_id": max_id})
                print(f"  ✅ {table_name}: 序列已重置为 {max_id + 1}")
            else:
                print(f"  ⏭️ {table_name}: 表中无数据，跳过序列重置")
        else:
            print(f"  ⏭️ {table_name}: 无自增序列，跳过")

    except Exception as e:
        print(f"  ❌ {table_name}: 修复序列时出错 - {e}")

postgres_db.commit()

sqlite_db.close()
postgres_db.close()

print("\n🎉 全部迁移完成！")
print("✅ 数据已迁移")
print("✅ 序列已修复")
print("✅ 现在可以正常添加新记录")