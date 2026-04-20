import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple


class RateLimiter:
    """速率限制器，用于控制 API 调用频率"""
    
    def __init__(self, max_calls: int, time_window: int):
        """
        初始化速率限制器
        
        Args:
            max_calls: 时间窗口内的最大调用次数
            time_window: 时间窗口大小（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: Dict[str, Deque[float]] = defaultdict(deque)
    
    def is_allowed(self, key: str) -> bool:
        """
        检查是否允许调用
        
        Args:
            key: 限制键（如 IP 地址或用户 ID）
            
        Returns:
            bool: 是否允许调用
        """
        current_time = time.time()
        
        # 清理过期的调用记录
        while self.calls[key] and current_time - self.calls[key][0] > self.time_window:
            self.calls[key].popleft()
        
        # 检查是否超过限制
        if len(self.calls[key]) < self.max_calls:
            self.calls[key].append(current_time)
            return True
        
        return False
    
    def get_remaining(self, key: str) -> int:
        """
        获取剩余的调用次数
        
        Args:
            key: 限制键
            
        Returns:
            int: 剩余的调用次数
        """
        current_time = time.time()
        
        # 清理过期的调用记录
        while self.calls[key] and current_time - self.calls[key][0] > self.time_window:
            self.calls[key].popleft()
        
        return max(0, self.max_calls - len(self.calls[key]))
    
    def get_reset_time(self, key: str) -> int:
        """
        获取限制重置时间
        
        Args:
            key: 限制键
            
        Returns:
            int: 重置时间（秒）
        """
        if not self.calls[key]:
            return 0
        
        oldest_call = self.calls[key][0]
        reset_time = oldest_call + self.time_window
        current_time = time.time()
        
        return max(0, int(reset_time - current_time))


class ProductRateLimiter:
    """商品级别的速率限制器"""
    
    def __init__(self, max_calls: int, time_window: int):
        """
        初始化商品速率限制器
        
        Args:
            max_calls: 时间窗口内的最大调用次数
            time_window: 时间窗口大小（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: Dict[str, Deque[float]] = defaultdict(deque)
    
    def is_allowed(self, product_id: str) -> bool:
        """
        检查是否允许为该商品调用 API
        
        Args:
            product_id: 商品 ID
            
        Returns:
            bool: 是否允许调用
        """
        current_time = time.time()
        
        # 清理过期的调用记录
        while self.calls[product_id] and current_time - self.calls[product_id][0] > self.time_window:
            self.calls[product_id].popleft()
        
        # 检查是否超过限制
        if len(self.calls[product_id]) < self.max_calls:
            self.calls[product_id].append(current_time)
            return True
        
        return False


# 全局速率限制器实例
api_rate_limiter = RateLimiter(max_calls=60, time_window=60)  # 每分钟 60 次
product_rate_limiter = ProductRateLimiter(max_calls=1, time_window=5)  # 每个商品每 5 秒 1 次
