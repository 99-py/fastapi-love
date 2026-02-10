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
from app.models import User,CouplePhoto
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from app.service.couple_service import (
    create_photo, delete_photo, toggle_favorite,
    today_memory, get_all_photos
)

router = APIRouter(prefix="/couple", tags=["Couple Photos"])
templates = Jinja2Templates(directory="app/templates")

# 上传目录配置
UPLOAD_DIR = "static/uploads/couple"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 允许的文件类型
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


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

    return templates.TemplateResponse(
        "album_couple_wall.html",
        {
            "request": request,
            "photos": photos,
            "total": total,
            "memory": memory,
            "current_user": user
        }
    )


@router.get("/wall/data")
def get_wall_data(
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        only_favorites: bool = Query(False),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """获取照片墙数据（API接口）"""
    photos, total = get_all_photos(
        db,
        page=page,
        per_page=per_page,
        only_favorites=only_favorites,
        user_id=user.id
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
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """上传合照"""
    try:
        # 验证文件类型
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                status_code=400,
                content={"error": f"不支持的文件类型，请使用: {', '.join(ALLOWED_EXTENSIONS)}"}
            )

        # 生成唯一文件名
        filename = f"{user.name}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # 保存文件
        with open(file_path, "wb") as buffer:
            content_bytes = await file.read()
            buffer.write(content_bytes)

        # 解析日期
        parsed_date = None
        if taken_date:
            try:
                parsed_date = datetime.strptime(taken_date, "%Y-%m-%d")
            except ValueError:
                pass

        # 创建数据库记录
        image_url = f"/static/uploads/couple/{filename}"
        photo = create_photo(
            db=db,
            user_id=user.id,
            image_url=image_url,
            caption=caption,
            memory=memory,
            location=location,
            taken_date=parsed_date
        )

        # 判断请求类型
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({
                "success": True,
                "message": "上传成功",
                "photo": {
                    "id": photo.id,
                    "image_url": photo.image_url,
                    "caption": photo.caption,
                    "memory": photo.memory,
                    "location": photo.location,
                    "created_at": photo.created_at.isoformat() if photo.created_at else None
                }
            })
        else:
            return RedirectResponse("album_couple_wall", status_code=303)

    except Exception as e:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=500,
                content={"error": f"上传失败: {str(e)}"}
            )
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.delete("/{photo_id}")
def delete_couple_photo(
        request: Request,
        photo_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """删除合照"""
    success, message = delete_photo(db, photo_id, user.id)

    if not success:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=403 if "无权限" in message else 404,
                content={"error": message}
            )
        raise HTTPException(
            status_code=403 if "无权限" in message else 404,
            detail=message
        )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({"success": True, "message": message})
    return RedirectResponse("album_couple_wall", status_code=303)


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
    return RedirectResponse("album_couple_wall", status_code=303)


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


# @router.get("/memory")
# def get_today_memory(
#         db: Session = Depends(get_db),
#         user: User = Depends(get_current_user)
# ):
#     """获取今日回忆"""
#     memory = today_memory(db, user.id)
#
#     if memory:
#         return {
#             "id": memory.id,
#             "image_url": memory.image_url,
#             "caption": memory.caption,
#             "memory": memory.memory,
#             "location": memory.location,
#             "created_at": memory.created_at.isoformat() if memory.created_at else None
#         }
#     return {"message": "今天还没有回忆哦"}