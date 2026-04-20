import time
from enum import Enum
from typing import Optional, Callable, Any


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"  # 闭合状态，允许请求
    OPEN = "open"  # 打开状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，允许部分请求


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 30,
                 reset_timeout: int = 60):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值，超过此值则熔断
            recovery_timeout: 恢复超时时间（秒），熔断后等待此时间进入半开状态
            reset_timeout: 重置超时时间（秒），半开状态下如果成功则重置熔断器
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.reset_timeout = reset_timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_state_change_time = 0
    
    def is_allowed(self) -> bool:
        """
        检查是否允许请求
        
        Returns:
            bool: 是否允许请求
        """
        current_time = time.time()
        
        # 检查是否需要从 OPEN 状态转换到 HALF_OPEN 状态
        if self.state == CircuitState.OPEN:
            if current_time - self.last_state_change_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change_time = current_time
                return True
            return False
        
        # 检查是否需要从 HALF_OPEN 状态转换到 CLOSED 状态
        elif self.state == CircuitState.HALF_OPEN:
            if current_time - self.last_state_change_time >= self.reset_timeout:
                self.reset()
                return True
            return True
        
        # CLOSED 状态，允许请求
        return True
    
    def record_success(self) -> None:
        """
        记录成功
        """
        if self.state == CircuitState.HALF_OPEN:
            # 半开状态下成功，重置熔断器
            self.reset()
        elif self.state == CircuitState.CLOSED:
            # 闭合状态下成功，重置失败计数
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """
        记录失败
        """
        current_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            # 闭合状态下失败，增加失败计数
            self.failure_count += 1
            self.last_failure_time = current_time
            
            # 检查是否达到失败阈值
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change_time = current_time
        
        elif self.state == CircuitState.HALF_OPEN:
            # 半开状态下失败，回到打开状态
            self.state = CircuitState.OPEN
            self.last_state_change_time = current_time
    
    def reset(self) -> None:
        """
        重置熔断器
        """
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.last_state_change_time = time.time()
    
    def get_state(self) -> CircuitState:
        """
        获取当前状态
        
        Returns:
            CircuitState: 当前状态
        """
        return self.state
    
    def get_failure_count(self) -> int:
        """
        获取失败计数
        
        Returns:
            int: 失败计数
        """
        return self.failure_count


class CircuitBreakerWrapper:
    """熔断器包装器，用于包装函数调用"""
    
    def __init__(self, circuit_breaker: CircuitBreaker):
        """
        初始化熔断器包装器
        
        Args:
            circuit_breaker: 熔断器实例
        """
        self.circuit_breaker = circuit_breaker
    
    def __call__(self, func: Callable) -> Callable:
        """
        包装函数
        
        Args:
            func: 要包装的函数
            
        Returns:
            Callable: 包装后的函数
        """
        def wrapper(*args, **kwargs):
            if not self.circuit_breaker.is_allowed():
                raise Exception("Circuit breaker is open, request denied")
            
            try:
                result = func(*args, **kwargs)
                self.circuit_breaker.record_success()
                return result
            except Exception as e:
                self.circuit_breaker.record_failure()
                raise
        
        return wrapper


# 全局熔断器实例
api_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    reset_timeout=60
)

# API 调用装饰器
circuit_breaker = CircuitBreakerWrapper(api_circuit_breaker)
