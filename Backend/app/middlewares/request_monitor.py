import time
import logging
from fastapi import Request
from app.core.monitoring import monitor

# 使用专门的监控日志记录器
logger = logging.getLogger("monitoring")


async def request_monitor_middleware(request: Request, call_next):
    """
    请求监控中间件，用于记录请求的响应时间和成功率
    """
    start_time = time.time()
    
    # 记录请求开始
    logger.info(f"Request started: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        response_time = time.time() - start_time
        
        # 记录成功请求
        monitor.record_request(success=True, response_time=response_time)
        
        # 记录请求完成
        logger.info(f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {response_time:.4f}s")
        
        # 添加响应时间到响应头
        response.headers["X-Response-Time"] = str(response_time)
        
        return response
    except Exception as e:
        response_time = time.time() - start_time
        
        # 记录失败请求
        monitor.record_request(success=False, response_time=response_time)
        
        # 记录请求失败
        logger.error(f"Request failed: {request.method} {request.url.path} - Error: {str(e)} - Time: {response_time:.4f}s")
        
        raise
