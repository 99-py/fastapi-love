# app/api/memory.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
import os
import uuid
from pathlib import Path

from app.db import get_db
from app.deps import get_current_user
from app.models import User, MemoryDay, MemorySnapshot
from app.schema.memory import (
    MemoryDayCreate, MemoryDayUpdate, MemoryDayResponse,
    MemorySnapshotCreate, MemoryDayStats
)
from app.service.memory_service import MemoryService
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/memories", tags=["纪念日"])
templates = Jinja2Templates(directory="app/templates")

# 上传目录配置
UPLOAD_DIR = "static/uploads/memory"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ========== HTML 页面路由 ==========
@router.get("/", response_class=HTMLResponse)
def memory_home(
        request: Request,
        db: Session = Depends(get_db)
):
    """纪念日首页"""
    user = request.session.get("username")
    if not user:
        return RedirectResponse("/login")

    # 获取当前用户
    current_user = db.query(User).filter(User.name == user).first()
    if not current_user:
        return RedirectResponse("/login")

    # 获取纪念日列表
    memory_days = MemoryService.get_memory_days(db, current_user.id)

    # 获取统计信息
    stats = MemoryService.get_memory_stats(db, current_user.id)

    # 获取即将到来的纪念日
    upcoming = MemoryService.get_upcoming_anniversaries(db, current_user.id, 30)

    # 定义颜色类函数
    def get_color_class(memory_type):
        """根据纪念日类型返回对应的CSS类名"""
        color_map = {
            "love": "color-love",
            "birthday": "color-birthday",
            "travel": "color-travel",
            "custom": "color-custom"
        }
        return color_map.get(memory_type, "color-custom")

    return templates.TemplateResponse(
        "memory.html",
        {
            "request": request,
            "memory_days": memory_days,
            "stats": stats,
            "upcoming": upcoming,
            "current_user": user,
            "today": date.today(),
            "page": "memory",
            "get_color_class": get_color_class  # 添加这个函数
        }
    )

@router.get("/create", response_class=HTMLResponse)
def create_memory_page(request: Request):
    """创建纪念日页面"""
    user = request.session.get("username")
    if not user:
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        "memory_create.html",
        {
            "request": request,
            "current_user": user,
            "today": date.today().isoformat(),
            "page": "memory"
        }
    )


@router.post("/create")
async def create_memory_day_form(
        request: Request,
        title: str = Form(...),
        date_str: str = Form(...),
        type: str = Form(...),
        description: Optional[str] = Form(None),
        icon: str = Form("❤️"),
        color: str = Form("#ff6b6b"),
        is_annual: bool = Form(True),
        db: Session = Depends(get_db)
):
    """通过表单创建纪念日"""
    user = request.session.get("username")
    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": "未登录"}
        )

    current_user = db.query(User).filter(User.name == user).first()
    if not current_user:
        return JSONResponse(
            status_code=401,
            content={"error": "用户不存在"}
        )

    try:
        # 解析日期
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # 验证日期不是未来
        if parsed_date > date.today():
            return JSONResponse(
                status_code=400,
                content={"error": "纪念日日期不能是未来日期"}
            )

        # 创建纪念日
        memory_day = MemoryDay(
            title=title,
            date=parsed_date,
            type=type,
            description=description,
            icon=icon,
            color=color,
            is_annual=is_annual,
            is_public=True,
            owner_id=current_user.id
        )

        db.add(memory_day)
        db.commit()
        db.refresh(memory_day)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({
                "success": True,
                "message": "创建成功",
                "memory_day": {
                    "id": memory_day.id,
                    "title": memory_day.title,
                    "date": memory_day.date.isoformat()
                }
            })

        return RedirectResponse("/memories", status_code=303)

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"日期格式错误: {str(e)}"}
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": f"创建失败: {str(e)}"}
        )

@router.get("/{memory_id}", response_class=HTMLResponse)
def memory_detail(
        request: Request,
        memory_id: int,
        db: Session = Depends(get_db)
):
    """纪念日详情页"""
    user = request.session.get("username")
    if not user:
        return RedirectResponse("/login")

    current_user = db.query(User).filter(User.name == user).first()
    if not current_user:
        return RedirectResponse("/login")

    # 获取纪念日详情
    detail = MemoryService.get_memory_day_detail(db, memory_id, current_user.id)
    if not detail:
        raise HTTPException(status_code=404, detail="纪念日不存在")

    return templates.TemplateResponse(
        "memory_detail.html",
        {
            "request": request,
            "memory": detail["memory"],
            "snapshots": detail["snapshots"],
            "stats": detail["stats"],
            "current_user": user,
            "today": date.today().isoformat(),
            "page": "memory"
        }
    )




@router.post("/{memory_id}/snapshot")
async def add_snapshot(
        request: Request,
        memory_id: int,
        year: int = Form(...),
        note: str = Form(""),
        image: UploadFile = File(None),
        weather: str = Form(""),
        mood: str = Form(""),
        location: str = Form(""),
        db: Session = Depends(get_db)
):
    """添加年轮记录"""
    user = request.session.get("username")
    if not user:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=401,
                content={"error": "未登录"}
            )
        return RedirectResponse("/login")

    current_user = db.query(User).filter(User.name == user).first()
    if not current_user:
        return RedirectResponse("/login")

    # 检查纪念日是否存在
    memory = db.query(MemoryDay).filter(
        MemoryDay.id == memory_id,
        MemoryDay.owner_id == current_user.id
    ).first()

    if not memory:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse(
                status_code=404,
                content={"error": "纪念日不存在"}
            )
        return RedirectResponse("/memories")  # ✅ 修复这里：改为 /memories

    # 处理图片上传
    image_url = None
    if image and image.filename:
        try:
            file_ext = Path(image.filename).suffix.lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

            if file_ext not in allowed_extensions:
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JSONResponse(
                        status_code=400,
                        content={"error": "不支持的文件格式"}
                    )
                return RedirectResponse(f"/memories/{memory_id}")  # ✅ 修复这里

            # 创建上传目录
            upload_dir = "static/uploads/memory"
            os.makedirs(upload_dir, exist_ok=True)

            # 生成文件名
            filename = f"{user}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}{file_ext}"
            file_path = os.path.join(upload_dir, filename)

            # 保存文件
            with open(file_path, "wb") as buffer:
                content = await image.read()
                buffer.write(content)

            image_url = f"/static/uploads/memory/{filename}"

        except Exception as e:
            print(f"图片上传失败: {e}")

    # 检查是否已存在该年的记录
    existing_snapshot = db.query(MemorySnapshot).filter(
        MemorySnapshot.memory_day_id == memory_id,
        MemorySnapshot.year == year
    ).first()

    if existing_snapshot:
        # 更新现有记录
        existing_snapshot.note = note
        existing_snapshot.image = image_url
        existing_snapshot.weather = weather
        existing_snapshot.mood = mood
        existing_snapshot.location = location
    else:
        # 创建新记录
        snapshot = MemorySnapshot(
            memory_day_id=memory_id,
            year=year,
            note=note,
            image=image_url,
            weather=weather,
            mood=mood,
            location=location,
            created_by=user
        )
        db.add(snapshot)

    db.commit()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({
            "success": True,
            "message": "记录已保存"
        })

    return RedirectResponse(f"/memories/{memory_id}", status_code=303)  # ✅ 修复这里
    return RedirectResponse(f"/memories/{memory_id}", status_code=303)

# ========== API 接口 ==========
@router.get("/api/list", response_model=List[MemoryDayResponse])
def get_memory_days_api(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        type: Optional[str] = None
):
    """获取纪念日列表（API）"""
    return MemoryService.get_memory_days(db, current_user.id, memory_type=type)


@router.get("/api/{memory_id}", response_model=MemoryDayResponse)
def get_memory_day_api(
        memory_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取单个纪念日详情（API）"""
    memory = MemoryService.get_memory_day_by_id(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(status_code=404, detail="纪念日不存在")
    return memory


@router.post("/api/", response_model=MemoryDayResponse, status_code=status.HTTP_201_CREATED)
def create_memory_day_api(
        memory_data: MemoryDayCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建纪念日（API）"""
    return MemoryService.create_memory_day(db, memory_data, current_user.id)


@router.put("/api/{memory_id}", response_model=MemoryDayResponse)
def update_memory_day_api(
        memory_id: int,
        memory_data: MemoryDayUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新纪念日（API）"""
    memory = MemoryService.update_memory_day(db, memory_id, memory_data, current_user.id)
    if not memory:
        raise HTTPException(status_code=404, detail="纪念日不存在")
    return memory


@router.delete("/api/{memory_id}")
def delete_memory_day_api(
        memory_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除纪念日（API）"""
    if not MemoryService.delete_memory_day(db, memory_id, current_user.id):
        raise HTTPException(status_code=404, detail="纪念日不存在")
    return {"message": "纪念日已删除"}


@router.post("/api/{memory_id}/snapshot")
def create_memory_snapshot_api(
        request: Request,
        memory_id: int,
        year: int = Form(...),
        note: str = Form(""),
        image: UploadFile = File(None),
        weather: str = Form(""),
        mood: str = Form(""),
        location: str = Form(""),
        db: Session = Depends(get_db)
):
    """创建年轮记录"""
    user = request.session.get("username")
    if not user:
        raise HTTPException(status_code=401, detail="未登录")

    # 检查纪念日是否存在
    current_user = db.query(User).filter(User.name == user).first()
    memory = MemoryService.get_memory_day_by_id(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(status_code=404, detail="纪念日不存在")

    # 处理图片上传
    image_url = None
    if image and image.filename:
        # 验证文件类型
        file_ext = Path(image.filename).suffix.lower()
        if file_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            raise HTTPException(status_code=400, detail="不支持的图片格式")

        # 生成文件名
        filename = f"{user}_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # 保存文件
        with open(file_path, "wb") as buffer:
            content = image.file.read()
            buffer.write(content)

        image_url = f"/static/uploads/memory/{filename}"

    # 创建年轮记录
    snapshot_data = MemorySnapshotCreate(
        year=year,
        note=note,
        image=image_url,
        weather=weather,
        mood=mood,
        location=location
    )

    snapshot = MemoryService.create_memory_snapshot(
        db, snapshot_data, memory_id, user
    )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JSONResponse({
            "success": True,
            "message": "记录已保存",
            "snapshot": {
                "id": snapshot.id,
                "year": snapshot.year,
                "note": snapshot.note,
                "image": snapshot.image,
                "weather": snapshot.weather,
                "mood": snapshot.mood,
                "location": snapshot.location,
                "created_by": snapshot.created_by,
                "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None
            }
        })

    return RedirectResponse(f"/memory/{memory_id}", status_code=303)


@router.get("/api/stats")
def get_memory_stats_api(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取纪念日统计（API）"""
    return MemoryService.get_memory_stats(db, current_user.id)


@router.get("/api/timeline")
def get_memory_timeline_api(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取时间线视图（API）"""
    return MemoryService.get_timeline_view(db, current_user.id)


@router.get("/api/upcoming")
def get_upcoming_anniversaries_api(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        days: int = 30
):
    """获取即将到来的纪念日（API）"""
    return MemoryService.get_upcoming_anniversaries(db, current_user.id, days)