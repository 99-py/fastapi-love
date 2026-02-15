# app/api/couple.py
from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.db import get_db
from app.deps import get_current_user
from app.models import User, CouplePhoto
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from app.service.couple_service import (
    create_photo, delete_photo, toggle_favorite,
    today_memory, get_all_photos, update_photo_info, get_user_stats
)
from app.service.image_service import CloudinaryService  # 新增导入

router = APIRouter(prefix="/couple", tags=["Couple Photos"])
templates = Jinja2Templates(directory="app/templates")

# 允许的文件类型
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']


@router.get("/wall", response_class=HTMLResponse)
def photo_wall(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """合照照片墙页面"""
    # 获取照片
    photos, total = get_all_photos(db, user_id=user.id)

    # 获取今日回忆
    memory = today_memory(db, user.id)

    # 获取用户统计
    stats = get_user_stats(db, user.id)

    return templates.TemplateResponse(
        "album_couple_wall.html",
        {
            "request": request,
            "photos": photos,
            "total": total,
            "memory": memory,
            "stats": stats,
            "current_user": user
        }
    )


@router.get("/wall/data")
def get_wall_data(
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        only_favorites: bool = Query(False),
        year: Optional[int] = Query(None),
        month: Optional[int] = Query(None),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """获取照片墙数据（API接口）"""
    photos, total = get_all_photos(
        db,
        user_id=user.id,
        page=page,
        per_page=per_page,
        only_favorites=only_favorites,
        year=year,
        month=month
    )

    # 格式化返回数据
    photo_list = []
    for photo in photos:
        photo_list.append({
            "id": photo.id,
            "image_url": photo.image_url,
            "caption": photo.caption or "",
            "memory": photo.memory or "",
            "location": photo.location or "",
            "taken_date": photo.taken_date.isoformat() if photo.taken_date else None,
            "created_at": photo.created_at.isoformat() if photo.created_at else None,
            "is_favorite": photo.is_favorite,
            "is_private": photo.is_private,
            "cloudinary_public_id": photo.cloudinary_public_id,
            "format": photo.format,
            "width": photo.width,
            "height": photo.height,
            "owner_id": photo.owner_id,
            "owner_name": photo.owner.name if photo.owner else "未知"
        })

    return {
        "photos": photo_list,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_more": (page * per_page) < total
    }


@router.post("/upload")
async def upload_photo(
        request: Request,
        file: UploadFile = File(...),
        caption: str = Form(""),
        memory: str = Form(""),
        location: str = Form(""),
        taken_date: str = Form(None),
        is_private: bool = Form(False),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """上传合照到Cloudinary"""
    try:
        print(f"🔄 开始上传合照 - 用户: {user.name} ({user.id})")

        # 验证文件类型
        if not file.filename:
            return JSONResponse(
                status_code=400,
                content={"error": "请选择文件"}
            )

        # 验证MIME类型
        if file.content_type not in ALLOWED_MIME_TYPES:
            return JSONResponse(
                status_code=400,
                content={"error": f"不支持的文件类型，请使用: {', '.join(ALLOWED_MIME_TYPES)}"}
            )

        # 验证文件扩展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                status_code=400,
                content={"error": f"不支持的文件扩展名，请使用: {', '.join(ALLOWED_EXTENSIONS)}"}
            )

        # 上传到Cloudinary
        upload_result = await CloudinaryService.upload_image(file, user.name, folder="love_app/couple")

        if not upload_result.get("success"):
            error_msg = upload_result.get("error", "上传失败")
            print(f"❌ Cloudinary上传失败: {error_msg}")
            return JSONResponse(
                status_code=400,
                content={"error": error_msg}
            )

        print(f"✅ Cloudinary上传成功: {upload_result.get('url')}")

        # 解析日期
        parsed_date = None
        if taken_date:
            try:
                parsed_date = datetime.strptime(taken_date, "%Y-%m-%d").date()
            except ValueError:
                print(f"⚠️ 日期解析失败，使用当前日期: {taken_date}")
                parsed_date = datetime.now().date()
        else:
            parsed_date = datetime.now().date()

        # 创建数据库记录
        photo = create_photo(
            db=db,
            user_id=user.id,
            cloudinary_public_id=upload_result.get("public_id"),
            image_url=upload_result.get("url"),
            format=upload_result.get("format"),
            width=upload_result.get("width"),
            height=upload_result.get("height"),
            bytes=upload_result.get("bytes"),
            caption=caption,
            memory=memory,
            location=location,
            taken_date=parsed_date
        )

        print(f"✅ 数据库记录创建成功 - ID: {photo.id}")

        # 返回响应
        photo_data = {
            "id": photo.id,
            "image_url": photo.image_url,
            "caption": photo.caption,
            "memory": photo.memory,
            "location": photo.location,
            "taken_date": photo.taken_date.isoformat() if photo.taken_date else None,
            "created_at": photo.created_at.isoformat() if photo.created_at else None,
            "is_favorite": photo.is_favorite,
            "is_private": photo.is_private,
            "cloudinary_public_id": photo.cloudinary_public_id,
            "format": photo.format
        }

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({
                "success": True,
                "message": "上传成功",
                "photo": photo_data
            })
        else:
            return RedirectResponse("/couple/wall", status_code=303)

    except Exception as e:
        db.rollback()
        print(f"❌ 上传失败: {str(e)}")
        import traceback
        traceback.print_exc()

        error_msg = f"上传失败: {str(e)}"
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=500,
                content={"error": error_msg}
            )
        raise HTTPException(status_code=500, detail=error_msg)


@router.put("/{photo_id}")
def update_photo(
        request: Request,
        photo_id: int,
        caption: Optional[str] = Form(None),
        memory: Optional[str] = Form(None),
        location: Optional[str] = Form(None),
        taken_date: Optional[str] = Form(None),
        is_private: Optional[bool] = Form(None),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """更新照片信息"""
    try:
        # 解析日期
        parsed_date = None
        if taken_date:
            try:
                parsed_date = datetime.strptime(taken_date, "%Y-%m-%d").date()
            except ValueError:
                parsed_date = None

        # 更新照片信息
        success, photo = update_photo_info(
            db=db,
            photo_id=photo_id,
            user_id=user.id,
            caption=caption,
            memory=memory,
            location=location,
            taken_date=parsed_date,
            is_private=is_private
        )

        if not success or not photo:
            return JSONResponse(
                status_code=404,
                content={"error": "照片不存在或无权修改"}
            )

        photo_data = {
            "id": photo.id,
            "caption": photo.caption,
            "memory": photo.memory,
            "location": photo.location,
            "taken_date": photo.taken_date.isoformat() if photo.taken_date else None,
            "is_private": photo.is_private,
            "updated_at": photo.updated_at.isoformat() if photo.updated_at else None
        }

        return JSONResponse({
            "success": True,
            "message": "更新成功",
            "photo": photo_data
        })

    except Exception as e:
        print(f"❌ 更新失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"更新失败: {str(e)}"}
        )


@router.delete("/{photo_id}")
def delete_couple_photo(
        request: Request,
        photo_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """删除合照（同时删除Cloudinary上的图片）"""
    success, message = delete_photo(db, photo_id, user.id)

    if not success:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=403 if "无权" in message else 404,
                content={"error": message}
            )
        raise HTTPException(
            status_code=403 if "无权" in message else 404,
            detail=message
        )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"success": True, "message": message})
    return RedirectResponse("/couple/wall", status_code=303)


@router.put("/{photo_id}/favorite")
def toggle_favorite_photo(
        request: Request,
        photo_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """切换收藏状态"""
    success, result = toggle_favorite(db, photo_id, user.id)

    if not success:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=404,
                content={"error": result}
            )
        raise HTTPException(status_code=404, detail=result)

    is_favorite = result
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({
            "success": True,
            "is_favorite": is_favorite,
            "message": "已收藏" if is_favorite else "已取消收藏"
        })
    return RedirectResponse("/couple/wall", status_code=303)


@router.get("/upload-form", response_class=HTMLResponse)
def show_upload_form(request: Request, user: User = Depends(get_current_user)):
    """显示上传表单"""
    if not user:
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        "couple/upload_form.html",
        {
            "request": request,
            "current_user": user
        }
    )


@router.get("/stats")
def get_stats(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """获取用户统计信息"""
    stats = get_user_stats(db, user.id)
    return JSONResponse(stats)


@router.get("/memory/today")
def get_today_memory(
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """获取今日回忆"""
    memory = today_memory(db, user.id)

    if memory:
        return JSONResponse({
            "success": True,
            "memory": {
                "id": memory.id,
                "image_url": memory.image_url,
                "caption": memory.caption,
                "memory": memory.memory,
                "location": memory.location,
                "taken_date": memory.taken_date.isoformat() if memory.taken_date else None,
                "created_at": memory.created_at.isoformat() if memory.created_at else None
            }
        })
    return JSONResponse({
        "success": True,
        "memory": None,
        "message": "今天还没有回忆哦"
    })