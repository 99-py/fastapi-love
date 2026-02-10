# app/service/memory_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
from app.models import MemoryDay, MemorySnapshot, User
from app.schema.memory import MemoryDayCreate, MemoryDayUpdate, MemorySnapshotCreate
import math


class MemoryService:
    """纪念日服务"""

    @staticmethod
    def calculate_days_since(memory_date: date, today: date = None) -> int:
        """计算从某个日期到现在的天数"""
        today = today or date.today()
        return (today - memory_date).days

    @staticmethod
    def calculate_years_since(memory_date: date, today: date = None) -> int:
        """计算经过的年数"""
        today = today or date.today()
        years = today.year - memory_date.year
        if (today.month, today.day) < (memory_date.month, memory_date.day):
            years -= 1
        return max(0, years)

    @staticmethod
    def get_next_anniversary_date(memory_date: date, today: date = None) -> date:
        """获取下一个周年纪念日"""
        today = today or date.today()
        this_year = memory_date.replace(year=today.year)

        if this_year >= today:
            return this_year
        else:
            return this_year.replace(year=today.year + 1)

    @staticmethod
    def get_days_to_next_anniversary(memory_date: date, today: date = None) -> int:
        """获取距离下一个周年纪念日的天数"""
        next_date = MemoryService.get_next_anniversary_date(memory_date, today)
        return (next_date - (today or date.today())).days

    # === 纪念日 CRUD ===

    @staticmethod
    def create_memory_day(
            db: Session,
            memory_data: MemoryDayCreate,
            user_id: int
    ) -> MemoryDay:
        """创建纪念日"""
        db_memory = MemoryDay(
            **memory_data.dict(),
            owner_id=user_id
        )
        db.add(db_memory)
        db.commit()
        db.refresh(db_memory)
        return db_memory

    @staticmethod
    def get_memory_days(
            db: Session,
            user_id: int,
            memory_type: Optional[str] = None,
            only_upcoming: bool = False,
            limit: int = None
    ) -> List[MemoryDay]:
        """获取用户的纪念日列表"""
        query = db.query(MemoryDay).filter(MemoryDay.owner_id == user_id)

        if memory_type:
            query = query.filter(MemoryDay.type == memory_type)

        if only_upcoming:
            # 获取30天内即将到来的纪念日
            today = date.today()
            query = query.filter(
                MemoryDay.is_annual == True,
                extract('month', MemoryDay.date) == today.month,
                extract('day', MemoryDay.date) >= today.day,
                extract('day', MemoryDay.date) <= (today + timedelta(days=30)).day
            )

        query = query.order_by(
            extract('month', MemoryDay.date),
            extract('day', MemoryDay.date)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def get_memory_day_by_id(db: Session, memory_id: int, user_id: int) -> Optional[MemoryDay]:
        """根据ID获取纪念日"""
        return db.query(MemoryDay).filter(
            MemoryDay.id == memory_id,
            MemoryDay.owner_id == user_id
        ).first()

    @staticmethod
    def update_memory_day(
            db: Session,
            memory_id: int,
            memory_data: MemoryDayUpdate,
            user_id: int
    ) -> Optional[MemoryDay]:
        """更新纪念日"""
        memory = MemoryService.get_memory_day_by_id(db, memory_id, user_id)
        if memory:
            update_data = memory_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(memory, field, value)
            memory.updated_at = datetime.now()
            db.commit()
            db.refresh(memory)
        return memory

    @staticmethod
    def delete_memory_day(db: Session, memory_id: int, user_id: int) -> bool:
        """删除纪念日"""
        memory = MemoryService.get_memory_day_by_id(db, memory_id, user_id)
        if memory:
            db.delete(memory)
            db.commit()
            return True
        return False

    # === 年轮记录 CRUD ===

    @staticmethod
    def create_memory_snapshot(
            db: Session,
            snapshot_data: MemorySnapshotCreate,
            memory_day_id: int,
            created_by: str
    ) -> MemorySnapshot:
        """创建年轮记录"""
        # 检查是否已存在该年的记录
        existing = db.query(MemorySnapshot).filter(
            MemorySnapshot.memory_day_id == memory_day_id,
            MemorySnapshot.year == snapshot_data.year
        ).first()

        if existing:
            # 更新现有记录
            for field, value in snapshot_data.dict(exclude_unset=True).items():
                setattr(existing, field, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # 创建新记录
            db_snapshot = MemorySnapshot(
                **snapshot_data.dict(),
                memory_day_id=memory_day_id,
                created_by=created_by
            )
            db.add(db_snapshot)
            db.commit()
            db.refresh(db_snapshot)
            return db_snapshot

    @staticmethod
    def get_memory_snapshots(
            db: Session,
            memory_day_id: int,
            user_id: int
    ) -> List[MemorySnapshot]:
        """获取纪念日的年轮记录"""
        # 验证用户权限
        memory = db.query(MemoryDay).filter(
            MemoryDay.id == memory_day_id,
            MemoryDay.owner_id == user_id
        ).first()

        if not memory:
            return []

        return db.query(MemorySnapshot).filter(
            MemorySnapshot.memory_day_id == memory_day_id
        ).order_by(MemorySnapshot.year.desc()).all()

    @staticmethod
    def get_snapshot_by_year(
            db: Session,
            memory_day_id: int,
            year: int,
            user_id: int
    ) -> Optional[MemorySnapshot]:
        """获取指定年份的年轮记录"""
        memory = db.query(MemoryDay).filter(
            MemoryDay.id == memory_day_id,
            MemoryDay.owner_id == user_id
        ).first()

        if not memory:
            return None

        return db.query(MemorySnapshot).filter(
            MemorySnapshot.memory_day_id == memory_day_id,
            MemorySnapshot.year == year
        ).first()

    @staticmethod
    def delete_snapshot(db: Session, snapshot_id: int, user_id: int) -> bool:
        """删除年轮记录"""
        snapshot = db.query(MemorySnapshot).join(MemoryDay).filter(
            MemorySnapshot.id == snapshot_id,
            MemoryDay.owner_id == user_id
        ).first()

        if snapshot:
            db.delete(snapshot)
            db.commit()
            return True
        return False

    # === 统计和计算 ===

    @staticmethod
    def get_memory_stats(db: Session, user_id: int) -> Dict:
        """获取纪念日统计信息"""
        today = date.today()

        # 总纪念日数
        total_memories = db.query(MemoryDay).filter(
            MemoryDay.owner_id == user_id
        ).count()

        # 按类型统计
        by_type = db.query(
            MemoryDay.type,
            func.count(MemoryDay.id).label('count')
        ).filter(MemoryDay.owner_id == user_id) \
            .group_by(MemoryDay.type).all()

        # 年轮记录总数
        total_snapshots = db.query(MemorySnapshot).join(MemoryDay).filter(
            MemoryDay.owner_id == user_id
        ).count()

        # 最早纪念日
        earliest = db.query(MemoryDay).filter(
            MemoryDay.owner_id == user_id
        ).order_by(MemoryDay.date.asc()).first()

        years_together = 0
        if earliest:
            years_together = MemoryService.calculate_years_since(earliest.date, today)

        # 即将到来的纪念日（30天内）
        upcoming_memories = MemoryService.get_memory_days(
            db, user_id, only_upcoming=True
        )

        return {
            "total_memories": total_memories,
            "by_type": dict(by_type),
            "total_snapshots": total_snapshots,
            "years_together": years_together,
            "upcoming_count": len(upcoming_memories),
            "upcoming_memories": upcoming_memories[:5]  # 最多5个
        }

    @staticmethod
    def get_timeline_view(db: Session, user_id: int) -> List[Dict]:
        """获取时间线视图"""
        memories = MemoryService.get_memory_days(db, user_id)
        result = []

        for memory in memories:
            if not memory.is_annual:
                continue

            years = memory.years_since
            for year_offset in range(years + 1):
                target_year = memory.date.year + year_offset
                anniversary_date = memory.date.replace(year=target_year)

                result.append({
                    "date": anniversary_date,
                    "memory_day": memory,
                    "year": target_year,
                    "is_original": year_offset == 0,
                    "snapshot": next(
                        (s for s in memory.snapshots if s.year == target_year),
                        None
                    )
                })

        # 按日期排序
        result.sort(key=lambda x: x["date"], reverse=True)
        return result

    @staticmethod
    def get_upcoming_anniversaries(db: Session, user_id: int, days: int = 30) -> List[Dict]:
        """获取即将到来的纪念日"""
        today = date.today()
        end_date = today + timedelta(days=days)

        memories = MemoryService.get_memory_days(db, user_id)
        result = []

        for memory in memories:
            if not memory.is_annual:
                continue

            next_date = memory.next_anniversary_date
            if next_date and today <= next_date <= end_date:
                result.append({
                    "memory_day": memory,
                    "date": next_date,
                    "days_until": (next_date - today).days
                })

        result.sort(key=lambda x: x["days_until"])
        return result

    @staticmethod
    def get_memory_day_detail(db: Session, memory_id: int, user_id: int) -> Optional[Dict]:
        """获取纪念日详情，包含统计信息"""
        memory = MemoryService.get_memory_day_by_id(db, memory_id, user_id)
        if not memory:
            return None

        # 获取年轮记录
        snapshots = MemoryService.get_memory_snapshots(db, memory_id, user_id)

        # 计算统计
        today = date.today()
        stats = {
            "days_since": MemoryService.calculate_days_since(memory.date, today),
            "years_since": MemoryService.calculate_years_since(memory.date, today),
            "total_snapshots": len(snapshots),
            "snapshots_by_year": {s.year: s for s in snapshots}
        }

        return {
            "memory": memory,
            "snapshots": snapshots,
            "stats": stats
        }