# app/api/album.py
import shutil
import time

import os

from fastapi import APIRouter, Request, Depends,Form,UploadFile,File
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, HTMLResponse, JSONResponse
from datetime import datetime

from app.db import get_db
from app.models import AlbumPhoto, AlbumComment
from fastapi.templating import Jinja2Templates
from collections import defaultdict
# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 允许的文件类型
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
UPLOAD_DIR = "static/uploads/album"
os.makedirs(UPLOAD_DIR, exist_ok=True)
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

@router.get("/timeline", response_class=HTMLResponse)  # 👉 对齐动态：添加response_class=HTMLResponse
def album_timeline(request: Request, db: Session = Depends(get_db)):
    user = request.session.get("username")
    if not user:
        return RedirectResponse("/login")

    # 1. 查询照片和评论（保留你的原有逻辑）
    photos = db.query(AlbumPhoto).order_by(AlbumPhoto.shoot_date.desc()).all()
    comments = db.query(AlbumComment).all()

    # 2. 构建评论映射（保留你的原有逻辑）
    comment_map = defaultdict(list)
    for c in comments:
        comment_map[c.photo_id].append(c)

    # 👉 对齐动态：封装照片字典列表（明确提取字段，和动态的view_moments一致，避免直接传模型对象）
    view_photos = []
    for p in photos:
        view_photos.append({
            "id": p.id,
            "user": p.user,
            "image": p.image,  # 👉 关键：和动态一致，直接提取image字段（路径已有效）
            "shoot_date": p.shoot_date,
            "memory": p.memory,
            "location": p.location,
        })

    # 3. 年月分组（基于封装后的view_photos，保留你的需求）
    timeline = defaultdict(list)
    for p in view_photos:
        key = p["shoot_date"].strftime("%Y-%m")  # 👉 注意：字典取值用[]，而非.
        timeline[key].append({
            "photo": p,
            "comments": comment_map.get(p["id"], [])  # 👉 字典取值用[]
        })

    # 👉 修复核心错误：将排序移到循环外（和动态一致，外层统一处理）
    sorted_timeline = dict(sorted(timeline.items(), key=lambda x: x[0], reverse=True))

    return templates.TemplateResponse(
        "album_timeline.html",
        {
            "request": request,
            "timeline": sorted_timeline,
            "current_user": user,
            "photos_count": len(photos),
            "users_count": len(set(p["user"] for p in view_photos)) if photos else 0  # 👉 字典取值用[]
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
    """上传照片处理函数 - 与动态模块保持一致"""
    user = request.session.get("username")
    if not user:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=401,
                content={"error": "未登录"}
            )
        return RedirectResponse("/login")

    try:
        # 调试信息
        print("=" * 50)
        print(f"🔄 开始上传照片")
        print(f"👤 用户: {user}")
        print(f"📄 原始文件名: {image.filename}")
        print(f"📁 上传目录: {UPLOAD_DIR}")
        print(f"📁 绝对路径: {os.path.abspath(UPLOAD_DIR)}")

        # 验证文件类型
        if not image.filename:
            return JSONResponse(
                status_code=400,
                content={"error": "请选择文件"}
            )

        # 获取文件扩展名
        file_ext = os.path.splitext(image.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                status_code=400,
                content={"error": f"不支持的文件类型，请使用: {', '.join(ALLOWED_EXTENSIONS)}"}
            )

        # 🔧 生成安全的文件名（与动态模块一致）
        # 使用时间戳 + 随机字符串
        timestamp = int(time.time())
        random_str = str(int(time.time() * 1000))[-6:]
        safe_filename = f"{user}_{timestamp}_{random_str}{file_ext}"

        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        print(f"📁 保存路径: {file_path}")
        print(f"📁 绝对保存路径: {os.path.abspath(file_path)}")

        # 保存文件
        with open(file_path, "wb") as buffer:
            content_bytes = await image.read()
            buffer.write(content_bytes)

        # 验证文件已保存
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✅ 文件保存成功")
            print(f"📊 文件大小: {file_size} 字节")
            print(f"✅ 文件存在: 是")
        else:
            print(f"❌ 文件保存失败")
            raise Exception("文件保存失败")

        # 解析日期
        try:
            parsed_date = datetime.strptime(shoot_date, "%Y-%m-%d")
        except ValueError:
            # 如果没有提供日期，使用今天
            parsed_date = datetime.now()

        # 🔧 生成图片URL（与动态模块一致）
        # 注意：这里使用 /static/uploads/album/ 开头
        image_url = f"/static/uploads/album/{safe_filename}"
        print(f"🌐 图片URL: {image_url}")

        # 创建数据库记录
        photo = AlbumPhoto(
            user=user,
            memory=memory,
            location=location if location else None,
            shoot_date=parsed_date,
            image=image_url
        )

        db.add(photo)
        db.commit()
        db.refresh(photo)

        print(f"✅ 数据库记录创建成功")
        print(f"🆔 照片ID: {photo.id}")
        print(f"📅 拍摄日期: {photo.shoot_date}")
        print("=" * 50)

        # 判断请求类型
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # AJAX请求返回JSON
            return JSONResponse({
                "success": True,
                "message": "上传成功",
                "photo": {
                    "id": photo.id,
                    "user": photo.user,
                    "image": photo.image,
                    "memory": photo.memory,
                    "location": photo.location,
                    "shoot_date": photo.shoot_date.isoformat() if photo.shoot_date else None
                }
            })
        else:
            # 普通表单提交重定向
            return RedirectResponse("/album/timeline", status_code=303)

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

        return templates.TemplateResponse(
            "upload_form.html",
            {
                "request": request,
                "error": error_msg,
                "current_user": user
            }
        )


# app/api/album.py

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
        return JSONResponse(
            status_code=401,
            content={"error": "未登录"}
        )

    # 检查照片是否存在
    photo = db.query(AlbumPhoto).filter(AlbumPhoto.id == photo_id).first()
    if not photo:
        return JSONResponse(
            status_code=404,
            content={"error": "照片不存在"}
        )

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

        # 🔧 判断请求类型
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # AJAX请求返回JSON
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
            # 普通表单提交重定向
            return RedirectResponse("/album/timeline", status_code=303)

    except Exception as e:
        db.rollback()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=500,
                content={"error": f"评论失败: {str(e)}"}
            )
        return RedirectResponse("/album/timeline", status_code=303)


@router.delete("/photo/{photo_id}")
async def delete_album_photo(
        request: Request,
        photo_id: int,
        db: Session = Depends(get_db)
):
    """删除照片（支持AJAX）"""
    user = request.session.get("username")
    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": "未登录"}
        )

    # 查询照片
    photo = db.query(AlbumPhoto).filter(
        AlbumPhoto.id == photo_id,
        AlbumPhoto.user == user  # 只能删除自己的照片
    ).first()

    if not photo:
        return JSONResponse(
            status_code=404,
            content={"error": "照片不存在或无权删除"}
        )

    try:
        # 删除相关评论
        db.query(AlbumComment).filter(AlbumComment.photo_id == photo_id).delete()

        # 删除照片记录
        db.delete(photo)
        db.commit()

        # 🔧 删除物理文件
        if photo.image:
            import os
            # 移除 /static/ 前缀，获取文件路径
            file_path = photo.image.lstrip('/static/')
            full_path = os.path.join("static", file_path)
            if os.path.exists(full_path):
                os.remove(full_path)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({
                "success": True,
                "message": "照片删除成功"
            })
        else:
            return RedirectResponse("/album/timeline", status_code=303)

    except Exception as e:
        db.rollback()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=500,
                content={"error": f"删除失败: {str(e)}"}
            )
        return RedirectResponse("/album/timeline", status_code=303)