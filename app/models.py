import enum

from sqlalchemy import Text, DateTime, Column, Integer, String, Boolean, Date, ForeignKey, Enum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.db import Base
from datetime import datetime, date


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    memory_days = relationship("MemoryDay", back_populates="owner", cascade="all, delete-orphan")


class Couple(Base):
    __tablename__ = "couples"

    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer)
    user2_id = Column(Integer)
    start_date = Column(String)


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True)
    shared = Column(Boolean, default=True)
    title = Column(String)
    done = Column(Boolean, default=False)

class Moment(Base):
    __tablename__ = "moments"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)      # me / her
    content = Column(Text, nullable=True)  # 文字
    image = Column(String, nullable=True)  # 图片 URL
    created_at = Column(DateTime, default=datetime.utcnow)

class AlbumPhoto(Base):
    __tablename__ = "album_photos"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)  # me / her

    memory = Column(String, nullable=False)     # 一句话回忆
    location = Column(String, nullable=True)    # 地点
    shoot_date = Column(DateTime, nullable=False)  # 拍摄日期

    image = Column(String, nullable=True)       # 图片路径
    created_at = Column(DateTime, default=datetime.now)

class AlbumComment(Base):
    __tablename__ = "album_comments"

    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer)
    user = Column(String, index=True)       # me / her
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class CouplePhoto(Base):
    __tablename__ = "couple_photos"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String, nullable=False)  # 图片路径
    caption = Column(String, default="")  # 描述
    is_favorite = Column(Boolean, default=False)  # 是否收藏
    is_private = Column(Boolean, default=False)  # 是否私密
    created_at = Column(DateTime, default=datetime.utcnow)  # 创建时间
    owner_id = Column(Integer, ForeignKey("users.id"))  # 上传者
    owner = relationship("User")  # 用户关系

    # 添加新字段
    location = Column(String, nullable=True)  # 拍摄地点
    taken_date = Column(DateTime, nullable=True)  # 拍摄日期
    tags = Column(String, nullable=True)  # 标签，用逗号分隔
    memory = Column(Text, nullable=True)  # 回忆故事


class MemoryDay(Base):
    """纪念日主表 - 时间锚点"""
    __tablename__ = "memory_days"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)  # 纪念日名称
    date = Column(Date, nullable=False)  # 原始日期
    type = Column(String(20), default="love")  # love/birthday/travel/custom
    description = Column(Text, nullable=True)  # 一句话意义
    icon = Column(String(50), default="❤️")  # 图标
    color = Column(String(20), default="#ff6b6b")  # 卡片颜色
    is_annual = Column(Boolean, default=True)  # 是否每年重复
    is_public = Column(Boolean, default=True)  # 是否公开
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    owner = relationship("User", back_populates="memory_days")
    snapshots = relationship("MemorySnapshot",
                             back_populates="memory_day",
                             cascade="all, delete-orphan",
                             order_by="desc(MemorySnapshot.year)")

    def __repr__(self):
        return f"<MemoryDay {self.title} ({self.date})>"

    @hybrid_property
    def days_since(self):
        """从纪念日开始到现在经过的天数"""
        if not self.date:
            return 0
        return (date.today() - self.date).days

    @hybrid_property
    def years_since(self):
        """经过的年数"""
        today = date.today()
        years = today.year - self.date.year
        if (today.month, today.day) < (self.date.month, self.date.day):
            years -= 1
        return max(0, years)

    @hybrid_property
    def next_anniversary_date(self):
        """下一个周年纪念日"""
        today = date.today()
        this_year = self.date.replace(year=today.year)

        if this_year >= today:
            return this_year
        else:
            return this_year.replace(year=today.year + 1)

    @hybrid_property
    def days_to_next_anniversary(self):
        """距离下一个周年纪念日的天数"""
        if not self.is_annual:
            return None
        return (self.next_anniversary_date - date.today()).days


class MemorySnapshot(Base):
    """纪念日年轮记录 - 每一年的瞬间"""
    __tablename__ = "memory_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    memory_day_id = Column(Integer, ForeignKey("memory_days.id", ondelete="CASCADE"))
    year = Column(Integer, nullable=False)  # 哪一年
    note = Column(Text, nullable=True)  # 今年的感悟
    image = Column(String(500), nullable=True)  # 图片URL
    weather = Column(String(20), nullable=True)  # 那天天气
    mood = Column(String(20), nullable=True)  # 心情
    location = Column(String(100), nullable=True)  # 地点
    created_by = Column(String(20))  # 谁添加的
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    memory_day = relationship("MemoryDay", back_populates="snapshots")

    def __repr__(self):
        return f"<MemorySnapshot {self.year}: {self.note[:30]}>"
