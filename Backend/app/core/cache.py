import hashlib
import json
from typing import Optional, Any
from datetime import datetime, timedelta


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, value: Any, expiry: datetime):
        """
        初始化缓存条目
        
        Args:
            value: 缓存值
            expiry: 过期时间
        """
        self.value = value
        self.expiry = expiry
    
    def is_expired(self) -> bool:
        """
        检查是否过期
        
        Returns:
            bool: 是否过期
        """
        return datetime.now() > self.expiry


class InMemoryCache:
    """内存缓存实现"""
    
    def __init__(self, default_ttl: int = 3600):
        """
        初始化内存缓存
        
        Args:
            default_ttl: 默认过期时间（秒）
        """
        self.default_ttl = default_ttl
        self.cache: dict[str, CacheEntry] = {}
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            prefix: 键前缀
            **kwargs: 键值对参数
            
        Returns:
            str: 生成的缓存键
        """
        # 对参数进行排序，确保相同参数生成相同的键
        sorted_kwargs = sorted(kwargs.items(), key=lambda x: x[0])
        kwargs_str = json.dumps(sorted_kwargs, ensure_ascii=False)
        hash_obj = hashlib.md5(kwargs_str.encode('utf-8'))
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[Any]: 缓存值，如果不存在或已过期则返回 None
        """
        entry = self.cache.get(key)
        if entry:
            if entry.is_expired():
                # 清理过期缓存
                del self.cache[key]
                return None
            return entry.value
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果为 None 则使用默认值
        """
        expiry = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
        self.cache[key] = CacheEntry(value, expiry)
    
    def delete(self, key: str) -> None:
        """
        删除缓存值
        
        Args:
            key: 缓存键
        """
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """
        清空所有缓存
        """
        self.cache.clear()
    
    def get_product_intro_key(self, product_params: dict, country: str, length: str) -> str:
        """
        生成商品简介缓存键
        
        Args:
            product_params: 商品参数
            country: 目标国家
            length: 简介长度
            
        Returns:
            str: 缓存键
        """
        return self._generate_key(
            "product_intro",
            product_params=product_params,
            country=country,
            length=length
        )
    
    def get_consumer_preferences_key(self, dataset_text: str, country_code: str) -> str:
        """
        生成消费者偏好缓存键
        
        Args:
            dataset_text: 数据集文本
            country_code: 国家代码
            
        Returns:
            str: 缓存键
        """
        # 对数据集文本进行哈希，避免键过长
        text_hash = hashlib.md5(dataset_text.encode('utf-8')).hexdigest()
        return self._generate_key(
            "consumer_preferences",
            text_hash=text_hash,
            country_code=country_code
        )


# 全局缓存实例
cache = InMemoryCache(default_ttl=3600)  # 默认缓存 1 小时
