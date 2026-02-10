# app/schema/memory.py
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, validator, Field
from enum import Enum


class MemoryType(str, Enum):
    LOVE = "love"
    BIRTHDAY = "birthday"
    TRAVEL = "travel"
    CUSTOM = "custom"


class MemoryDayBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    date: date
    type: MemoryType = MemoryType.LOVE
    description: Optional[str] = Field(None, max_length=500)
    icon: str = "❤️"
    color: str = "#ff6b6b"
    is_annual: bool = True
    is_public: bool = True

    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('纪念日标题不能为空')
        return v.strip()

    @validator('date')
    def date_not_future(cls, v):
        if v > date.today():
            raise ValueError('纪念日日期不能是未来日期')
        return v


class MemoryDayCreate(MemoryDayBase):
    pass


class MemoryDayUpdate(MemoryDayBase):
    pass


class MemorySnapshotBase(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    note: Optional[str] = Field(None, max_length=1000)
    image: Optional[str] = None
    weather: Optional[str] = None
    mood: Optional[str] = None
    location: Optional[str] = None

    @validator('year')
    def year_reasonable(cls, v):
        if v < 2000 or v > date.today().year:
            raise ValueError('年份必须在 2000 到今年之间')
        return v


class MemorySnapshotCreate(MemorySnapshotBase):
    pass


class MemorySnapshotInDB(MemorySnapshotBase):
    id: int
    memory_day_id: int
    created_by: str
    created_at: datetime

    class Config:
        orm_mode = True


class MemoryDayInDB(MemoryDayBase):
    id: int
    owner_id: int
    days_since: int
    years_since: int
    days_to_next_anniversary: Optional[int]
    next_anniversary_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    snapshots: List[MemorySnapshotInDB] = []

    class Config:
        orm_mode = True


# 响应模型
class MemoryDayResponse(MemoryDayInDB):
    pass


class MemoryDayStats(BaseModel):
    total_memories: int
    total_snapshots: int
    years_together: int
    upcoming_count: int
    by_type: dict


class MemoryDayWithStats(MemoryDayInDB):
    stats: Optional[MemoryDayStats] = None