import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.endpoints import router as api_router
from app.core.db_init import init_market_knowledge
from app.core.database import close_connection
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    # 启动时初始化 MongoDB 数据
    logger.info("正在连接 MongoDB 并初始化市场知识库...")
    await init_market_knowledge()
    logger.info("MongoDB 初始化完成")
    yield
    # 关闭时释放连接
    await close_connection()


app = FastAPI(
    title="跨境电商产品简介生成API",
    version="2.0",
    lifespan=lifespan,
)

# 配置跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


# 自定义422日志输出
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.getLogger("uvicorn.error").error(
        f"请求验证失败 URL={request.url} body={exc.body} errors={exc.errors()}"
    )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "服务正常运行"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
