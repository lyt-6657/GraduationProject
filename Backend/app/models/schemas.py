from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum


class IntroLength(str, Enum):
    short = "short"    # ~100字
    medium = "medium"  # ~300字
    long = "long"      # ~500字


class ProductInfo(BaseModel):
    """产品信息模型"""
    title: str = ""
    description: Optional[str] = ""
    parameters: Optional[Dict] = {}
    competitor_features: Optional[List[str]] = []
    country: Optional[str] = ""
    audience: Optional[str] = ""


class MarketInfo(BaseModel):
    """市场信息模型"""
    country: str
    audience: Optional[str] = ""
    target_language: Optional[str] = "English"


class GenerateIntroRequest(BaseModel):
    """生成简介请求模型"""
    product_info: ProductInfo
    market_info: MarketInfo
    intro_length: Optional[IntroLength] = IntroLength.medium


class GenerateIntroResponse(BaseModel):
    """生成简介响应模型"""
    success: bool
    key_features: Optional[List[str]] = []
    product_intro: Optional[str] = ""
    evaluation: Optional[Dict[str, float]] = None
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
    lang: str = "en"
    error: Optional[str] = ""
