from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict
from enum import Enum


class IntroLength(str, Enum):
    short = "short"    # ~100字
    medium = "medium"  # ~300字
    long = "long"      # ~500字


class ProductInfo(BaseModel):
    """产品信息模型"""
    title: str
    description: Optional[str] = ""
    parameters: Optional[Dict] = {}
    competitor_features: Optional[List[str]] = []

    @field_validator("title")
    def title_not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("标题不能为空")
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
    intro_length: Optional[IntroLength] = IntroLength.medium
    product_url: Optional[str] = ""


class GenerateIntroResponse(BaseModel):
    """生成简介响应模型"""
    success: bool
    key_features: Optional[List[str]] = []
    product_intro: Optional[str] = ""
    error: Optional[str] = ""


class CountryOption(BaseModel):
    """国家选项"""
    country_code: str
    country_name: str
    region: str
    target_language: str


class CountriesResponse(BaseModel):
    """国家列表响应"""
    countries: List[CountryOption]


class FetchProductUrlRequest(BaseModel):
    """URL抓取请求"""
    url: str


class FetchProductUrlResponse(BaseModel):
    """URL抓取响应"""
    success: bool
    product_info: Optional[ProductInfo] = None
    error: Optional[str] = ""


class ExtractPreferencesRequest(BaseModel):
    """消费者偏好提取请求"""
    dataset_text: str
    country_code: Optional[str] = None


class ExtractPreferencesResponse(BaseModel):
    """消费者偏好提取响应"""
    success: bool
    country_not_found: Optional[bool] = False
    data: Optional[Dict] = None
    error: Optional[str] = ""


class UploadDatasetResponse(BaseModel):
    """数据集文件上传响应"""
    success: bool
    filename: str = ""
    text_preview: str = ""
    char_count: int = 0
    full_text: str = ""
    error: Optional[str] = ""
