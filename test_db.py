# test_db.py
import os
import sys

sys.path.append('.')

from app.db import SessionLocal, engine
from sqlalchemy import inspect, text


def test_connection():
    """测试数据库连接和表结构"""
    try:
        # 测试连接
        with engine.connect() as conn:
            print(f"✅ 数据库连接成功")
            print(f"数据库类型: {engine.url.drivername}")

            # 检查表结构
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"✅ 数据库中的表: {tables}")

            # 检查特定表的字段
            for table in ['album_photos', 'moments', 'couple_photos']:
                if table in tables:
                    columns = inspector.get_columns(table)
                    print(f"\n📊 {table} 表的字段:")
                    for col in columns:
                        print(f"  - {col['name']} ({col['type']})")

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")


if __name__ == "__main__":
    test_connection()