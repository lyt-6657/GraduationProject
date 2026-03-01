import uvicorn
from fastapi import FastAPI
from app.api.endpoints import router as api_router

# 初始化FastAPI应用
app = FastAPI(title="跨境电商产品简介生成API", version="1.0")

# 注册路由
app.include_router(api_router)

# 健康检查接口（基础版）
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "服务正常运行"}

# 启动服务
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True  # 开发模式热重载
    )