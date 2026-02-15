import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app import models

# PostgreSQL 引擎
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ 错误: 请设置 DATABASE_URL 环境变量")
    print("例如: export DATABASE_URL=postgresql://user:password@host/dbname")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()


def get_all_tables():
    """获取所有ORM模型的表名"""
    tables = []
    for attr in dir(models):
        obj = getattr(models, attr)
        if hasattr(obj, "__tablename__"):
            tables.append(obj.__tablename__)
    return tables


def fix_sequence_for_table(table_name, db_session):
    """修复单个表的序列"""
    try:
        # 1. 检查表是否有自增序列
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

        result = db_session.execute(text(check_seq_sql), {"table_name": table_name})
        has_sequence = result.scalar()

        if not has_sequence:
            return False, f"表 {table_name} 没有自增ID列"

        # 2. 获取序列名称
        get_seq_name_sql = """
        SELECT pg_get_serial_sequence('public.' || :table_name, 'id')
        """
        result = db_session.execute(text(get_seq_name_sql), {"table_name": table_name})
        seq_name = result.scalar()

        if not seq_name:
            return False, f"表 {table_name} 的序列名称无法获取"

        # 提取序列名称（去除模式名）
        if '.' in seq_name:
            seq_name = seq_name.split('.')[1]

        # 3. 获取当前最大ID
        max_id_sql = text(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}"')
        result = db_session.execute(max_id_sql)
        max_id = result.scalar()

        # 4. 获取序列当前值
        current_seq_sql = text(f"SELECT last_value FROM {seq_name}")
        result = db_session.execute(current_seq_sql)
        current_seq = result.scalar()

        print(f"\n📊 {table_name}:")
        print(f"   最大ID: {max_id}")
        print(f"   序列当前值: {current_seq}")

        if max_id >= current_seq:
            # 5. 重置序列
            reset_sql = text(f"SELECT setval('{seq_name}', :new_value, false)")
            new_value = max_id + 1
            db_session.execute(reset_sql, {"new_value": new_value})

            # 6. 验证重置结果
            result = db_session.execute(current_seq_sql)
            new_seq_value = result.scalar()

            return True, f"序列已从 {current_seq} 重置为 {new_seq_value}"
        else:
            return True, f"序列正常 (max_id={max_id}, current_seq={current_seq})"

    except Exception as e:
        return False, f"错误: {str(e)}"


def main():
    print("🔧 开始修复 PostgreSQL 序列问题")
    print(f"连接数据库: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

    # 获取所有表
    tables = get_all_tables()
    print(f"\n找到 {len(tables)} 个表: {', '.join(tables)}")

    fixed_tables = []
    failed_tables = []

    # 修复每个表的序列
    for table_name in tables:
        success, message = fix_sequence_for_table(table_name, db)

        if success:
            print(f"   ✅ {message}")
            fixed_tables.append(table_name)
        else:
            print(f"   ❌ {table_name}: {message}")
            failed_tables.append((table_name, message))

    # 提交更改
    try:
        db.commit()
        print("\n✅ 所有更改已提交")
    except Exception as e:
        print(f"\n❌ 提交更改时出错: {e}")
        db.rollback()
        return

    # 显示总结
    print(f"\n📋 修复完成:")
    print(f"   ✅ 成功修复: {len(fixed_tables)} 个表")

    if failed_tables:
        print(f"   ❌ 失败: {len(failed_tables)} 个表")
        for table_name, error in failed_tables:
            print(f"      - {table_name}: {error}")

    # 测试插入
    print("\n🧪 测试序列修复效果...")
    test_table = None
    for table in tables:
        if table == 'album_comments':  # 用出问题的表测试
            test_table = table
            break

    if test_table:
        try:
            # 尝试获取下一个序列值
            test_sql = text(f"SELECT nextval('{test_table}_id_seq')")
            result = db.execute(test_sql)
            next_val = result.scalar()
            print(f"   ✅ {test_table} 下一个序列值: {next_val}")
        except Exception as e:
            print(f"   ❌ 测试序列失败: {e}")

    db.close()
    print("\n🎉 修复完成！现在可以正常添加新记录了。")


if __name__ == "__main__":
    main()