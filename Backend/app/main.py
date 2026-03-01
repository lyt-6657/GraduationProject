import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request
from app.api.endpoints import router as api_router

app = FastAPI(
    title="跨境电商产品简介生成API",
    version="1.0",
)

# 配置跨域（允许前端地址的所有请求方法和头）
app.add_middleware(
    CORSMiddleware,
    # 开发时可使用["*"]，或按需列出前端地址/端口
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

# 自定义422日志输出，便于调试前端请求内容
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 记录请求体和错误详情
    import logging
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