from pathlib import Path

from app.db import Base, engine, SessionLocal
from app.models import User,Couple
from app.api.weather import router as weather_router
from app.api.page import router as page_router
from fastapi import FastAPI,Request
from app.api.todo import router as todo_router
from app.api.love import router as love_router
from app.api.auth import router as auth_router
from app.api import memory
# from app.api import anniversary
from app.api import auth, todo, page, weather, couple
from starlette.middleware.sessions import SessionMiddleware
import logging
import time
import os
from fastapi.staticfiles import StaticFiles
from app.api import album
from app.api import moment
from app.api import couple
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


app = FastAPI(title="Couple Todo Service")
os.makedirs("static/uploads/moments", exist_ok=True)
# 尝试两种配置方式
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("✅ 静态文件配置: static")
except:
    try:
        app.mount("/static", StaticFiles(directory="app/static"), name="static")
        print("✅ 静态文件配置: app/static")
    except Exception as e:
        print(f"❌ 静态文件配置失败: {e}")
app.add_middleware(
    SessionMiddleware,
    secret_key="love-secret-key"  # 开发期写死没问题
)
BASE_DIR = Path(__file__).parent
# 注册路由
app.include_router(todo_router)
app.include_router(couple.router,prefix="/couple",tags=["Couple Photos"])
app.include_router(weather_router, prefix="/weather", tags=["Weather"])
app.include_router(page_router)
app.include_router(love_router)
app.include_router(auth_router)
app.include_router(weather.router)
app.include_router(moment.router)
app.include_router(album.router)
app.include_router(memory.router, tags=["纪念日"])
# app.include_router(anniversary.router)
app.include_router(couple.router,tags=["Couple Photos"])
# 建表
Base.metadata.create_all(bind=engine)
# 种子数据（开发期）
def init_demo_data():
    db = SessionLocal()
    if not db.query(User).first():
        me = User(name="me")
        her = User(name="her")
        db.add_all([me, her])
        db.commit()
        db.refresh(me)
        db.refresh(her)

        couple = Couple(
            user1_id=me.id,
            user2_id=her.id,
            start_date="2023-01-01"
        )
        db.add(couple)
        db.commit()
    db.close()

init_demo_data()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"响应状态: {response.status_code} | 耗时: {process_time:.4f}s")
        return response
    except Exception as e:
        logger.error(f"请求处理异常: {e}")
        raise
