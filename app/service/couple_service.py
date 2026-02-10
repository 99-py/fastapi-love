# app/service/couple_service.py
from datetime import datetime, timedelta
from sqlalchemy import extract, desc, asc
import random
from sqlalchemy.orm import Session
from app.models import CouplePhoto, User
import os
from pathlib import Path


def create_photo(db: Session, user_id: int, image_url: str, caption: str = "",
                 memory: str = None, location: str = None, taken_date: datetime = None):
    """创建合照记录"""
    photo = CouplePhoto(
        owner_id=user_id,
        image_url=image_url,
        caption=caption,
        memory=memory,
        location=location,
        taken_date=taken_date or datetime.utcnow(),
        created_at=datetime.utcnow()
    )

    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def delete_photo(db: Session, photo_id: int, user_id: int):
    """删除合照"""
    photo = db.query(CouplePhoto).filter(CouplePhoto.id == photo_id).first()

    if not photo:
        return False, "照片不存在"

    if photo.owner_id != user_id:
        return False, "无权限删除"

    # 删除物理文件
    try:
        if photo.image_url and photo.image_url.startswith("/static/"):
            file_path = photo.image_url.lstrip("/")
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"删除文件失败: {e}")

    db.delete(photo)
    db.commit()
    return True, "删除成功"


def toggle_favorite(db: Session, photo_id: int, user_id: int):
    """切换收藏状态"""
    photo = db.query(CouplePhoto).filter(
        CouplePhoto.id == photo_id,
        CouplePhoto.owner_id == user_id
    ).first()

    if not photo:
        return False, "照片不存在或无权限"

    photo.is_favorite = not photo.is_favorite
    db.commit()
    return True, photo.is_favorite


def today_memory(db: Session, user_id: int = None):
    """获取今日回忆"""
    today = datetime.utcnow()

    # 查询条件
    query = db.query(CouplePhoto)

    if user_id:
        query = query.filter(CouplePhoto.owner_id == user_id)

    photos = query.filter(
        extract('month', CouplePhoto.created_at) == today.month,
        extract('day', CouplePhoto.created_at) == today.day
    ).all()

    if photos:
        return random.choice(photos)
    return None


def get_photos_by_user(db: Session, user_id: int, page: int = 1, per_page: int = 20):
    """获取用户的合照"""
    offset = (page - 1) * per_page
    photos = db.query(CouplePhoto).filter(
        CouplePhoto.owner_id == user_id
    ).order_by(
        CouplePhoto.created_at.desc()
    ).offset(offset).limit(per_page).all()

    total = db.query(CouplePhoto).filter(
        CouplePhoto.owner_id == user_id
    ).count()

    return photos, total


def get_all_photos(db: Session, page: int = 1, per_page: int = 20,
                   only_favorites: bool = False, user_id: int = None):
    """获取所有合照"""
    offset = (page - 1) * per_page
    query = db.query(CouplePhoto)

    if only_favorites:
        query = query.filter(CouplePhoto.is_favorite == True)

    if user_id:
        query = query.filter(CouplePhoto.owner_id == user_id)

    photos = query.order_by(
        CouplePhoto.created_at.desc()
    ).offset(offset).limit(per_page).all()

    total = query.count()

    return photos, total