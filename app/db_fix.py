# app/db_fix.py
import os
import time
from sqlalchemy import text, create_engine
import logging

logger = logging.getLogger(__name__)


def fix_database():
    """修复数据库表结构和事务问题"""
    print("🔧 开始修复数据库...")

    # 获取数据库URL
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ 未找到 DATABASE_URL")
        return False

    # 创建独立的连接（不使用连接池）
    engine = create_engine(
        DATABASE_URL,
        poolclass=None,
        isolation_level="AUTOCOMMIT"
    )

    try:
        with engine.connect() as conn:
            # 1. 检查并修复表结构
            print("📊 检查表结构...")

            tables_to_check = {
                'moments': [
                    ('cloudinary_public_id', 'VARCHAR(255)', ''),
                    ('image_url', 'VARCHAR(500)', "image"),
                    ('format', 'VARCHAR(10)', ''),
                    ('width', 'INTEGER', ''),
                    ('height', 'INTEGER', ''),
                    ('bytes', 'INTEGER', '')
                ],
                'album_photos': [
                    ('cloudinary_public_id', 'VARCHAR(255)', ''),
                    ('image_url', 'VARCHAR(500)', "image"),
                    ('format', 'VARCHAR(10)', '')
                ],
                'couple_photos': [
                    ('cloudinary_public_id', 'VARCHAR(255)', ''),
                    ('image_url', 'VARCHAR(500)', ''),
                    ('format', 'VARCHAR(10)', ''),
                    ('width', 'INTEGER', ''),
                    ('height', 'INTEGER', ''),
                    ('bytes', 'INTEGER', '')
                ]
            }

            for table_name, columns in tables_to_check.items():
                print(f"  📁 检查 {table_name} 表...")

                # 检查表是否存在
                check_table = text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table_name}'
                    )
                """)
                table_exists = conn.execute(check_table).scalar()

                if not table_exists:
                    print(f"    ⚠️  {table_name} 表不存在")
                    continue

                for column_name, column_type, old_column in columns:
                    # 检查列是否存在
                    check_column = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' 
                        AND column_name = '{column_name}'
                    """)
                    column_exists = conn.execute(check_column).fetchone()

                    if column_exists:
                        print(f"    ✅ {column_name} 已存在")
                    else:
                        # 添加列
                        try:
                            add_sql = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'
                            conn.execute(text(add_sql))
                            print(f"    ➕ 添加 {column_name}")

                            # 如果有旧列数据，迁移数据
                            if old_column:
                                try:
                                    migrate_sql = f"""
                                    UPDATE {table_name} 
                                    SET {column_name} = {old_column} 
                                    WHERE {old_column} IS NOT NULL 
                                    AND {column_name} IS NULL
                                    """
                                    conn.execute(text(migrate_sql))
                                    print(f"    📦 迁移 {old_column} -> {column_name}")
                                except Exception as migrate_error:
                                    print(f"    ⚠️  数据迁移失败: {migrate_error}")

                        except Exception as add_error:
                            print(f"    ❌ 添加 {column_name} 失败: {add_error}")

            print("🎉 数据库修复完成！")
            return True

    except Exception as e:
        print(f"❌ 数据库修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False