from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict

class ProductInfo(BaseModel):
    """产品信息模型"""
    title: str
    # 描述改为可选，前端未提供也不会触发422
    description: Optional[str] = ""
    parameters: Optional[Dict] = {}  # 兜底空字典
    competitor_features: Optional[List[str]] = []  # 兜底空列表

    # 非空校验（针对非空值）
    @field_validator("title", "description")
    def not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("标题/描述不能为空")
        return v

class MarketInfo(BaseModel):
    """市场信息模型"""
    country: str
    audience: Optional[str] = ""
    target_language: Optional[str] = "English"

    @field_validator("country")
    def country_not_empty(cls, v):
        if not v.strip():
            raise ValueError("目标国家不能为空")
        return v

class GenerateIntroRequest(BaseModel):
    """生成简介请求模型"""
    product_info: ProductInfo
    market_info: MarketInfo

class GenerateIntroResponse(BaseModel):
    """生成简介响应模型"""
    success: bool
    key_features: Optional[List[str]] = []
    product_intro: Optional[str] = ""
    error: Optional[str] = ""