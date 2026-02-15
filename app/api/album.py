# app/api/album.py
import shutil
import time

import os

from fastapi import APIRouter, Request, Depends,Form,UploadFile,File
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, HTMLResponse, JSONResponse
from datetime import datetime

from app.db import get_db
from app.models import AlbumPhoto, AlbumComment
from fastapi.templating import Jinja2Templates
from collections import defaultdict

from app.service.image_service import CloudinaryService

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 允许的文件类型
# 允许的文件类型
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']

router = APIRouter(prefix="/album", tags=["Album"])
templates = Jinja2Templates(directory="app/templates")

@router.get("")
def album_home(request: Request):
    user = request.session.get("username")
    if not user:
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        "album.html",
        {"request": request}
    )


@router.get("/timeline", response_class=HTMLResponse)
def album_timeline(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("username")
    if not user:
        return RedirectResponse("/login")

    # 查询照片和评论
    try:
        photos = db.query(AlbumPhoto).order_by(AlbumPhoto.shoot_date.desc()).all()
    except Exception as e:
        # 回滚并使用备用查询
        print(f"⚠️ 查询失败，回滚事务并使用备用查询: {e}")
        db.rollback()

        query = text("""
            SELECT id, "user", memory, location, shoot_date, image, created_at
            FROM album_photos 
            ORDER BY shoot_date DESC
        """)
        result = db.execute(query)
        photos = []
        for row in result:
            photos.append({
                "id": row.id,
                "user": row.user,
                "memory": row.memory,
                "location": row.location,
                "shoot_date": row.shoot_date,
                "image": row.image,
                "image_url": row.image,  # 映射
                "created_at": row.created_at
            })
    comments = db.query(AlbumComment).all()

    # 构建评论映射
    comment_map = defaultdict(list)
    for c in comments:
        comment_map[c.photo_id].append(c)

    # 封装照片数据
    view_photos = []
    for p in photos:
        # 使用Cloudinary的图片URL
        image_url = p.image_url
        # 如果需要缩略图，可以这样：
        # thumbnail_url = CloudinaryService.get_image_url(p.cloudinary_public_id, width=300, height=300)

        view_photos.append({
            "id": p.id,
            "user": p.user,
            "image": image_url,
            "shoot_date": p.shoot_date,
            "memory": p.memory,
            "location": p.location,
            "public_id": p.cloudinary_public_id,  # 用于删除操作
            "format": p.format,
            "created_at": p.created_at
        })

    # 年月分组
    timeline = defaultdict(list)
    for p in view_photos:
        key = p["shoot_date"].strftime("%Y-%m")
        timeline[key].append({
            "photo": p,
            "comments": comment_map.get(p["id"], [])
        })

    sorted_timeline = dict(sorted(timeline.items(), key=lambda x: x[0], reverse=True))

    return templates.TemplateResponse(
        "album_timeline.html",
        {
            "request": request,
            "timeline": sorted_timeline,
            "current_user": user,
            "photos_count": len(photos),
            "users_count": len(set(p["user"] for p in view_photos)) if photos else 0
        }
    )


# ✅ 1. GET 方法：显示上传表单
@router.get("/timeline/upload", response_class=HTMLResponse)
async def show_upload_form(request: Request):
    """显示上传表单页面"""
    user = request.session.get("username")
    if not user:
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        "upload_form.html",
        {
            "request": request,
            "current_user": user
        }
    )


@router.post("/timeline/upload")
async def upload_album_photo(
        request: Request,
        memory: str = Form(...),
        location: str = Form(""),
        shoot_date: str = Form(...),
        image: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """上传照片到Cloudinary"""
    user = request.session.get("username")
    if not user:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(status_code=401, content={"error": "未登录"})
        return RedirectResponse("/login")

    try:
        print(f"🔄 开始上传照片 - 用户: {user}")

        # 验证文件类型
        if not image.filename:
            return JSONResponse(status_code=400, content={"error": "请选择文件"})

        # 验证MIME类型
        if image.content_type not in ALLOWED_MIME_TYPES:
            return JSONResponse(
                status_code=400,
                content={"error": f"不支持的文件类型，请使用: {', '.join(ALLOWED_MIME_TYPES)}"}
            )

        # 验证文件扩展名
        file_ext = os.path.splitext(image.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                status_code=400,
                content={"error": f"不支持的文件扩展名，请使用: {', '.join(ALLOWED_EXTENSIONS)}"}
            )

        # 上传到Cloudinary
        upload_result = await CloudinaryService.upload_image(image, user)

        if not upload_result.get("success"):
            error_msg = upload_result.get("error", "上传失败")
            return JSONResponse(status_code=400, content={"error": error_msg})

        print(f"✅ Cloudinary上传成功: {upload_result.get('url')}")

        # 解析日期
        try:
            parsed_date = datetime.strptime(shoot_date, "%Y-%m-%d")
        except ValueError:
            parsed_date = datetime.now()

        # 保存到数据库
        photo = AlbumPhoto(
            user=user,
            memory=memory,
            location=location if location else None,
            shoot_date=parsed_date,
            cloudinary_public_id=upload_result.get("public_id"),
            image_url=upload_result.get("url"),
            format=upload_result.get("format")
        )

        db.add(photo)
        db.commit()
        db.refresh(photo)

        print(f"✅ 数据库记录创建成功 - ID: {photo.id}")

        # 返回响应
        photo_data = {
            "id": photo.id,
            "user": photo.user,
            "image": photo.image_url,
            "memory": photo.memory,
            "location": photo.location,
            "shoot_date": photo.shoot_date.isoformat() if photo.shoot_date else None,
            "public_id": photo.cloudinary_public_id,
            "format": photo.format
        }

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({
                "success": True,
                "message": "上传成功",
                "photo": photo_data
            })
        else:
            return RedirectResponse("/album/timeline", status_code=303)

    except Exception as e:
        db.rollback()
        print(f"❌ 上传失败: {str(e)}")
        import traceback
        traceback.print_exc()

        error_msg = f"上传失败: {str(e)}"
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(status_code=500, content={"error": error_msg})

        return templates.TemplateResponse(
            "upload_form.html",
            {
                "request": request,
                "error": error_msg,
                "current_user": user
            }
        )


@router.delete("/photo/{photo_id}")
async def delete_album_photo(
        request: Request,
        photo_id: int,
        db: Session = Depends(get_db)
):
    """删除照片（同时删除Cloudinary上的文件）"""
    user = request.session.get("username")
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        # 查询照片
        photo = db.query(AlbumPhoto).filter(
            AlbumPhoto.id == photo_id,
            AlbumPhoto.user == user  # 只能删除自己的照片
        ).first()

        if not photo:
            return JSONResponse(status_code=404, content={"error": "照片不存在或无权删除"})

        # 从Cloudinary删除图片
        if photo.cloudinary_public_id:
            delete_result = CloudinaryService.delete_image(photo.cloudinary_public_id)
            if not delete_result.get("success"):
                print(f"⚠️ Cloudinary删除失败: {delete_result.get('error')}")
                # 继续删除数据库记录，避免僵尸记录

        # 删除相关评论
        db.query(AlbumComment).filter(AlbumComment.photo_id == photo_id).delete()

        # 删除照片记录
        db.delete(photo)
        db.commit()

        print(f"✅ 照片删除成功 - ID: {photo_id}")

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({
                "success": True,
                "message": "照片删除成功"
            })
        else:
            return RedirectResponse("/album/timeline", status_code=303)

    except Exception as e:
        db.rollback()
        print(f"❌ 删除失败: {str(e)}")

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(status_code=500, content={"error": f"删除失败: {str(e)}"})
        return RedirectResponse("/album/timeline", status_code=303)


# app/api/album.py

# 评论功能保持不变
@router.post("/timeline/comment")
async def add_album_comment(
        request: Request,
        photo_id: int = Form(...),
        content: str = Form(...),
        db: Session = Depends(get_db)
):
    """添加评论（支持AJAX）"""
    user = request.session.get("username")
    if not user:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    # 检查照片是否存在
    photo = db.query(AlbumPhoto).filter(AlbumPhoto.id == photo_id).first()
    if not photo:
        return JSONResponse(status_code=404, content={"error": "照片不存在"})

    # 创建评论
    comment = AlbumComment(
        photo_id=photo_id,
        user=user,
        content=content,
        created_at=datetime.now()
    )

    try:
        db.add(comment)
        db.commit()
        db.refresh(comment)

        # 判断请求类型
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({
                "success": True,
                "message": "评论成功",
                "comment": {
                    "id": comment.id,
                    "user": comment.user,
                    "content": comment.content,
                    "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        else:
            return RedirectResponse("/album/timeline", status_code=303)

    except Exception as e:
        db.rollback()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(status_code=500, content={"error": f"评论失败: {str(e)}"})
        return RedirectResponse("/album/timeline", status_code=303)