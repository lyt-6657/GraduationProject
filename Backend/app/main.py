import uvicorn
import os
import logging
import codecs
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.endpoints import router as api_router
from app.core.db_init import init_market_knowledge
from app.core.database import close_connection
from app.core.preference_extractor import log_local_model_config
from app.core.config import config
from app.middlewares.request_monitor import request_monitor_middleware

# 配置日志
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
MONITOR_LOG_DIR = os.path.join(LOG_DIR, "monitoring")
EVALUATION_LOG_DIR = os.path.join(LOG_DIR, "evaluation")

# 创建日志目录
os.makedirs(MONITOR_LOG_DIR, exist_ok=True)
os.makedirs(EVALUATION_LOG_DIR, exist_ok=True)

# 配置全链路监控日志
monitoring_logger = logging.getLogger("monitoring")
monitoring_logger.setLevel(logging.INFO)

# 创建文件处理器（指定编码为utf-8）
monitoring_handler = logging.FileHandler(os.path.join(MONITOR_LOG_DIR, "monitoring.log"), encoding='utf-8')
monitoring_handler.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
# 设置控制台处理器的编码为utf-8
if hasattr(console_handler, 'setEncoding'):
    console_handler.setEncoding('utf-8')

# 配置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
monitoring_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器
if not monitoring_logger.handlers:
    monitoring_logger.addHandler(monitoring_handler)
    monitoring_logger.addHandler(console_handler)

# 配置评估日志
evaluation_logger = logging.getLogger("evaluation")
evaluation_logger.setLevel(logging.INFO)

# 创建自定义的FileHandler，确保文件以UTF-8编码打开
class UTF8FileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        super().__init__(filename, mode, encoding, delay)

# 创建评估日志文件处理器（指定编码为utf-8，并以写入模式打开）
evaluation_handler = UTF8FileHandler(
    os.path.join(EVALUATION_LOG_DIR, "evaluation.log"), 
    mode='w'  # 以写入模式打开，确保文件以正确编码创建
)
evaluation_handler.setLevel(logging.INFO)

# 配置评估日志格式
evaluation_formatter = logging.Formatter('%(asctime)s - %(message)s')
evaluation_handler.setFormatter(evaluation_formatter)

# 添加评估日志处理器
if not evaluation_logger.handlers:
    evaluation_logger.addHandler(evaluation_handler)

# 配置根日志的编码
for handler in logging.root.handlers:
    if hasattr(handler, 'setEncoding'):
        handler.setEncoding('utf-8')

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    # 启动时初始化 MongoDB 数据
    logger.info("正在连接 MongoDB 并初始化市场知识库...")
    await init_market_knowledge()
    logger.info("MongoDB 初始化完成")
    log_local_model_config()
    
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

# 添加请求监控中间件
app.middleware("http")(request_monitor_middleware)

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
    from app.core.monitoring import monitor
    health_status = monitor.check_service_health()
    return {
        "status": "healthy",
        "message": "服务正常运行",
        "metrics": health_status
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
