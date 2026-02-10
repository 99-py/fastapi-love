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

router = APIRouter(prefix="/moments", tags=["Moments"])

# 确保模板目录正确
templates = Jinja2Templates(directory="app/templates")

# 上传目录配置
UPLOAD_DIR = "static/uploads/moments"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
            "image": m.image,
            "created_at": m.created_at,
            "is_owner": m.user == user  # ⭐ 核心
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
    """创建动态"""
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
        image_path = None
        if image and image.filename:
            # 验证文件类型
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            ext = Path(image.filename).suffix.lower()

            if ext not in allowed_extensions:
                return JSONResponse(
                    status_code=400,
                    content={"error": "不支持的文件类型"}
                )

            # 生成唯一文件名
            filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # 保存文件
            with open(file_path, "wb") as buffer:
                content_bytes = await image.read()
                buffer.write(content_bytes)

            image_path = f"/static/uploads/moments/{filename}"

        # 创建动态记录 - 使用本地时间
        now = datetime.now()

        moment = Moment(
            user=user,
            content=content,
            image=image_path,
            created_at=now
        )

        db.add(moment)
        db.commit()
        db.refresh(moment)

        # 判断请求类型
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # AJAX 请求返回 JSON
            return {
                "success": True,
                "message": "发布成功",
                "moment": {
                    "id": moment.id,
                    "user": moment.user,
                    "content": moment.content,
                    "image": moment.image,
                    "created_at": moment.created_at.isoformat() if moment.created_at else None
                }
            }
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
            "image": m.image,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "is_owner": m.user == user  # 添加 is_owner 字段
        }
        result.append(moment_data)

    return result


# ========== 以下路由没有设置默认值 ==========
@router.get("/{moment_id}")
def get_moment(moment_id: int, db: Session = Depends(get_db)):  # ✅ 正确：没有默认值
    """获取单个动态"""
    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if not moment:
        raise HTTPException(status_code=404, detail="动态不存在")
    return moment


@router.put("/{moment_id}")
def update_moment(
        moment_id: int,  # ✅ 正确：没有默认值
        content: str = Form(...),
        db: Session = Depends(get_db)
):
    """更新动态"""
    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if not moment:
        raise HTTPException(status_code=404, detail="动态不存在")

    moment.content = content
    db.commit()
    db.refresh(moment)
    return moment


@router.delete("/{moment_id}")
def delete_moment(moment_id: int, db: Session = Depends(get_db)):  # ✅ 正确：没有默认值
    """删除动态"""
    moment = db.query(Moment).filter(Moment.id == moment_id).first()
    if not moment:
        raise HTTPException(status_code=404, detail="动态不存在")

    db.delete(moment)
    db.commit()
    return {"message": "删除成功"}