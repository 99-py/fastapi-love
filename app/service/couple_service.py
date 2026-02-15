from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, date
from typing import Optional, Tuple, List
from app.models import CouplePhoto, User
from app.service.image_service  import CloudinaryService  # 新增导入
import os


def create_photo(
        db: Session,
        user_id: int,
        cloudinary_public_id: str,  # 新增参数
        image_url: str,  # 新增参数
        format: str,  # 新增参数
        width: int,  # 新增参数
        height: int,  # 新增参数
        bytes: int,  # 新增参数
        caption: str = "",
        memory: str = "",
        location: str = "",
        taken_date: Optional[date] = None
) -> CouplePhoto:
    """
    创建合照记录（使用Cloudinary）
    """
    photo = CouplePhoto(
        owner_id=user_id,
        cloudinary_public_id=cloudinary_public_id,
        image_url=image_url,
        format=format,
        width=width,
        height=height,
        bytes=bytes,
        caption=caption,
        memory=memory,
        location=location,
        taken_date=taken_date or datetime.now().date()
    )

    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def delete_photo(db: Session, photo_id: int, user_id: int) -> Tuple[bool, str]:
    """
    删除合照（同时删除Cloudinary上的图片）
    """
    photo = db.query(CouplePhoto).filter(
        CouplePhoto.id == photo_id,
        CouplePhoto.owner_id == user_id
    ).first()

    if not photo:
        return False, "照片不存在或无权删除"

    try:
        # 从Cloudinary删除图片
        if photo.cloudinary_public_id:
            delete_result = CloudinaryService.delete_image(photo.cloudinary_public_id)
            if not delete_result.get("success"):
                # 记录错误但不阻止删除数据库记录
                print(f"Cloudinary删除失败: {delete_result.get('error')}")

        # 删除数据库记录
        db.delete(photo)
        db.commit()
        return True, "照片删除成功"

    except Exception as e:
        db.rollback()
        return False, f"删除失败: {str(e)}"


def get_all_photos(
        db: Session,
        user_id: int,
        page: int = 1,
        per_page: int = 20,
        only_favorites: bool = False,
        year: Optional[int] = None,
        month: Optional[int] = None
) -> Tuple[List[CouplePhoto], int]:
    """
    获取用户的所有合照（支持分页和筛选）
    """
    query = db.query(CouplePhoto).filter(CouplePhoto.owner_id == user_id)

    # 筛选收藏
    if only_favorites:
        query = query.filter(CouplePhoto.is_favorite == True)

    # 按年月筛选
    if year:
        query = query.filter(db.extract('year', CouplePhoto.taken_date) == year)
    if month:
        query = query.filter(db.extract('month', CouplePhoto.taken_date) == month)

    # 排序和分页
    query = query.order_by(desc(CouplePhoto.taken_date), desc(CouplePhoto.created_at))

    total = query.count()
    photos = query.offset((page - 1) * per_page).limit(per_page).all()

    return photos, total


def toggle_favorite(db: Session, photo_id: int, user_id: int) -> Tuple[bool, bool]:
    """
    切换收藏状态
    """
    photo = db.query(CouplePhoto).filter(
        CouplePhoto.id == photo_id,
        CouplePhoto.owner_id == user_id
    ).first()

    if not photo:
        return False, False

    photo.is_favorite = not photo.is_favorite
    db.commit()
    return True, photo.is_favorite


def today_memory(db: Session, user_id: int) -> Optional[CouplePhoto]:
    """
    获取今天的回忆（同一天拍摄的随机一张照片）
    """
    today = datetime.now().date()

    # 查找同一天的照片
    photo = db.query(CouplePhoto).filter(
        CouplePhoto.owner_id == user_id,
        db.func.date(CouplePhoto.taken_date) == today
    ).order_by(db.func.random()).first()

    return photo


def get_photo_by_id(db: Session, photo_id: int, user_id: int) -> Optional[CouplePhoto]:
    """
    根据ID获取照片（检查权限）
    """
    return db.query(CouplePhoto).filter(
        CouplePhoto.id == photo_id,
        CouplePhoto.owner_id == user_id
    ).first()


def update_photo_info(
        db: Session,
        photo_id: int,
        user_id: int,
        caption: Optional[str] = None,
        memory: Optional[str] = None,
        location: Optional[str] = None,
        taken_date: Optional[date] = None,
        is_private: Optional[bool] = None
) -> Tuple[bool, Optional[CouplePhoto]]:
    """
    更新照片信息
    """
    photo = get_photo_by_id(db, photo_id, user_id)
    if not photo:
        return False, None

    if caption is not None:
        photo.caption = caption
    if memory is not None:
        photo.memory = memory
    if location is not None:
        photo.location = location
    if taken_date is not None:
        photo.taken_date = taken_date
    if is_private is not None:
        photo.is_private = is_private

    photo.updated_at = datetime.now()
    db.commit()
    db.refresh(photo)

    return True, photo


def get_user_stats(db: Session, user_id: int) -> dict:
    """
    获取用户统计信息
    """
    total = db.query(CouplePhoto).filter(CouplePhoto.owner_id == user_id).count()
    favorites = db.query(CouplePhoto).filter(
        CouplePhoto.owner_id == user_id,
        CouplePhoto.is_favorite == True
    ).count()

    # 获取最早和最晚照片日期
    earliest = db.query(CouplePhoto.taken_date).filter(
        CouplePhoto.owner_id == user_id
    ).order_by(CouplePhoto.taken_date).first()

    latest = db.query(CouplePhoto.taken_date).filter(
        CouplePhoto.owner_id == user_id
    ).order_by(desc(CouplePhoto.taken_date)).first()

    return {
        "total_photos": total,
        "favorite_photos": favorites,
        "earliest_date": earliest[0] if earliest else None,
        "latest_date": latest[0] if latest else None,
        "years": db.query(
            db.extract('year', CouplePhoto.taken_date).distinct()
        ).filter(CouplePhoto.owner_id == user_id).all()
    }