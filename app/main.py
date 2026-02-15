from pathlib import Path
from dotenv import load_dotenv
from app.db import Base, engine, SessionLocal
from app.models import User,Couple
from app.api.weather import router as weather_router
from app.api.page import router as page_router
from fastapi import FastAPI,Request
from app.api.todo import router as todo_router
from app.api.love import router as love_router
from app.api.auth import router as auth_router
from app.api import memory
from app.db_migration import run_migrations
from app.init_db import init_database
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
load_dotenv()
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

# 或者用try-except包裹
try:
    init_demo_data()
except Exception as e:
    print(f"⚠️ 初始化数据失败: {e}")
    print("应用继续启动，不影响主要功能")
print("Cloud Name:", os.getenv("CLOUDINARY_CLOUD_NAME"))


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("🚀 应用启动中...")
    run_migrations()  # 添加这行
    # 打印环境变量检查
    import os
    print(f"Cloud Name: {os.getenv('CLOUDINARY_CLOUD_NAME', '未设置')}")

    # 初始化数据库（捕获所有异常，不影响启动）
    try:
        init_database()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"⚠️ 数据库初始化警告: {e}")
        # 继续启动，可能表已经存在

    # 不再调用 init_demo_data()，或者用更安全的方式
    try:
        # from app.init_data import init_demo_data
        init_demo_data()
        print("✅ 示例数据初始化完成")
    except Exception as e:
        print(f"⚠️ 示例数据初始化失败: {e}")
        # 继续启动，不影响主要功能
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
