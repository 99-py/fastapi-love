# app/init_db.py
from app.db import Base, engine
import logging

logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库表结构"""
    try:
        # 创建所有表（如果不存在）
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表初始化完成")

        # # 检查并添加Cloudinary字段（如果缺少）
        # from sqlalchemy import inspect
        # from sqlalchemy.schema import AddColumn
        # from sqlalchemy import String, Integer

        # inspector = inspect(engine)

        # tables_to_check = ['album_photos', 'moments', 'couple_photos']
        # field_configs = {
        #     'album_photos': [
        #         ('cloudinary_public_id', String(255)),
        #         ('image_url', String(500)),
        #         ('format', String(10))
        #     ],
        #     'moments': [
        #         ('cloudinary_public_id', String(255)),
        #         ('image_url', String(500)),
        #         ('format', String(10)),
        #         ('width', Integer),
        #         ('height', Integer),
        #         ('bytes', Integer)
        #     ],
        #     'couple_photos': [
        #         ('cloudinary_public_id', String(255)),
        #         ('image_url', String(500)),
        #         ('format', String(10)),
        #         ('width', Integer),
        #         ('height', Integer),
        #         ('bytes', Integer)
        #     ]
        # }

        # for table_name, fields in field_configs.items():
        #     if inspector.has_table(table_name):
        #         existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
        #
        #         for field_name, field_type in fields:
        #             if field_name not in existing_columns:
        #                 logger.info(f"添加字段 {table_name}.{field_name}")
        #                 # 在实际应用中，这里应该使用Alembic
        #                 # 但作为备份方案，我们记录信息

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
