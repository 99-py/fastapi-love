# app/api/moment.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import os
import uuid
from pathlib import Path
from app.db import get_db
from app.models import Moment
from app.service.image_service import CloudinaryService  # 新增导入

router = APIRouter(prefix="/moments", tags=["Moments"])

# 确保模板目录正确
templates = Jinja2Templates(directory="app/templates")

# 允许的文件类型
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']


# ========== 页面路由 ==========
@router.get("/timeline", response_class=HTMLResponse)
def timeline(request: Request, db: Session = Depends(get_db)):
    """动态页面"""
    # 检查用户是否登录
    user = request.session.get("username")
    if not user:
        return RedirectResponse("/login")

    # 获取所有动态，按时间倒序
    moments = db.query(Moment).order_by(Moment.created_at.desc()).all()
    view_moments = []
    for m in moments:
        view_moments.append({
            "id": m.id,
            "user": m.user,  # 明确是 username
            "content": m.content,
            "image": m.image_url,  # 使用Cloudinary的image_url
            "created_at": m.created_at,
            "is_owner": m.user == user,  # ⭐ 核心
            "format": m.format,  # 新增：图片格式
            "cloudinary_public_id": m.cloudinary_public_id  # 新增：Cloudinary ID
        })
    return templates.TemplateResponse(
        "timeline.html",
        {
            "request": request,
            "moments": view_moments,
            "current_user": user,
            "page": "timeline"
        }
    )


# ========== API 路由 ==========
@router.post("/")
async def create_moment(
        request: Request,
        content: str = Form(...),
        image: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    """创建动态（使用Cloudinary存储图片）"""
    # 检查用户是否登录
    user = request.session.get("username")
    if not user:
        # 如果是 AJAX 请求
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=401,
                content={"error": "未登录"}
            )
        return RedirectResponse("/login")

    try:
        # 处理图片上传
        cloudinary_public_id = None
        image_url = None
        format = None
        width = None
        height = None
        file_bytes = None

        if image and image.filename:
            # 验证文件类型
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            ext = Path(image.filename).suffix.lower()

            if ext not in allowed_extensions:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"不支持的文件类型，请使用: {', '.join(allowed_extensions)}"}
                )

            # 验证MIME类型
            if image.content_type not in ALLOWED_MIME_TYPES:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"不支持的文件类型，请使用: {', '.join(ALLOWED_MIME_TYPES)}"}
                )

            # 上传到Cloudinary
            upload_result = await CloudinaryService.upload_image(image, user, folder="love_app/moments")

            if not upload_result.get("success"):
                error_msg = upload_result.get("error", "上传失败")
                return JSONResponse(
                    status_code=400,
                    content={"error": error_msg}
                )

            cloudinary_public_id = upload_result.get("public_id")
            image_url = upload_result.get("url")
            format = upload_result.get("format")
            width = upload_result.get("width")
            height = upload_result.get("height")
            file_bytes = upload_result.get("bytes")

        # 创建动态记录 - 使用本地时间
        now = datetime.now()

        moment = Moment(
            user=user,
            content=content,
            cloudinary_public_id=cloudinary_public_id,
            image_url=image_url,
            format=format,
            width=width,
            height=height,
            bytes=file_bytes,
            created_at=now
        )

        db.add(moment)
        db.commit()
        db.refresh(moment)

        # 判断请求类型
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # AJAX 请求返回 JSON
            return JSONResponse({
                "success": True,
                "message": "发布成功",
                "moment": {
                    "id": moment.id,
                    "user": moment.user,
                    "content": moment.content,
                    "image": moment.image_url,
                    "created_at": moment.created_at.isoformat() if moment.created_at else None,
                    "cloudinary_public_id": moment.cloudinary_public_id,
                    "format": moment.format
                }
            })
        else:
            # 普通表单提交重定向
            return RedirectResponse("/moments/timeline", status_code=303)

    except Exception as e:
        db.rollback()
        print(f"发布失败: {e}")

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=500,
                content={"error": f"发布失败: {str(e)}"}
            )
        return RedirectResponse("/moments/timeline?error=发布失败", status_code=303)


@router.get("/")
def list_moments(request: Request, db: Session = Depends(get_db)):
    """获取动态列表（API接口）"""
    user = request.session.get("username")
    moments = db.query(Moment).order_by(Moment.created_at.desc()).all()

    result = []
    for m in moments:
        moment_data = {
            "id": m.id,
            "user": m.user,
            "content": m.content,
            "image": m.image_url,  # 使用Cloudinary的image_url
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "is_owner": m.user == user,  # 添加 is_owner 字段
            "cloudinary_public_id": m.cloudinary_public_id,
            "format": m.format
        }
        result.append(moment_data)

    return result


# ========== 以下路由需要修改删除逻辑 ==========
@router.get("/{moment_id}")
def get_moment(moment_id: int, db: Session = Depends(get_db)):
    """获取单个动态"""
    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if not moment:
        raise HTTPException(status_code=404, detail="动态不存在")

    # 返回包含Cloudinary信息的数据
    return {
        "id": moment.id,
        "user": moment.user,
        "content": moment.content,
        "image": moment.image_url,
        "cloudinary_public_id": moment.cloudinary_public_id,
        "format": moment.format,
        "created_at": moment.created_at
    }


@router.put("/{moment_id}")
def update_moment(
        request: Request,
        moment_id: int,
        content: str = Form(...),
        db: Session = Depends(get_db)
):
    """更新动态"""
    user = request.session.get("username")
    if not user:
        raise HTTPException(status_code=401, detail="未登录")

    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if not moment:
        raise HTTPException(status_code=404, detail="动态不存在")

    # 检查权限
    if moment.user != user:
        raise HTTPException(status_code=403, detail="无权修改此动态")

    moment.content = content
    db.commit()
    db.refresh(moment)

    return {
        "success": True,
        "message": "更新成功",
        "moment": {
            "id": moment.id,
            "content": moment.content,
            "image": moment.image_url,
            "created_at": moment.created_at.isoformat() if moment.created_at else None
        }
    }


@router.delete("/{moment_id}")
async def delete_moment(
        request: Request,
        moment_id: int,
        db: Session = Depends(get_db)
):
    """删除动态（同时删除Cloudinary上的图片）"""
    user = request.session.get("username")
    if not user:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=401,
                content={"error": "未登录"}
            )
        raise HTTPException(status_code=401, detail="未登录")

    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if not moment:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=404,
                content={"error": "动态不存在"}
            )
        raise HTTPException(status_code=404, detail="动态不存在")

    # 检查权限
    if moment.user != user:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=403,
                content={"error": "无权删除此动态"})