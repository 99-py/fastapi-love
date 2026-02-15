# app/db_migration.py
import logging
from sqlalchemy import text, inspect
from app.db import engine

logger = logging.getLogger(__name__)

def run_migrations():
    """检查并添加缺失的数据库列"""
    with engine.connect() as conn:
        inspector = inspect(engine)

        # 1. 检查并修复 moments 表
        if 'moments' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('moments')]
            if 'cloudinary_public_id' not in columns:
                logger.info("在 moments 表中添加 cloudinary_public_id 列...")
                conn.execute(text("""
                    ALTER TABLE moments 
                    ADD COLUMN cloudinary_public_id VARCHAR(255)
                """))
                conn.commit()

        # 2. 检查并修复 album_photos 表
        if 'album_photos' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('album_photos')]
            if 'cloudinary_public_id' not in columns:
                logger.info("在 album_photos 表中添加 cloudinary_public_id 列...")
                conn.execute(text("""
                    ALTER TABLE album_photos 
                    ADD COLUMN cloudinary_public_id VARCHAR(255)
                """))
                conn.commit()

    logger.info("✅ 数据库迁移检查完成")