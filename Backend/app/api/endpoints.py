import logging
import chardet
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.models.schemas import (
    GenerateIntroRequest,
    GenerateIntroResponse,
    CountriesResponse,
    CountryOption,
    ExtractPreferencesRequest,
    ExtractPreferencesResponse,
    UploadDatasetResponse,
    ProductInfo,
)
from app.core.feature_extractor import FeatureExtractor
from app.core.prompt_builder import PromptBuilder
from app.core.llm_client import LLMClient
from app.core.localization import LocalizationAdapter
from app.core.preference_extractor import PreferenceExtractor
from app.core.database import get_market_knowledge_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["产品简介生成"])

feature_extractor = FeatureExtractor()
prompt_builder = PromptBuilder()
llm_client = LLMClient()
localization_adapter = LocalizationAdapter()
preference_extractor = PreferenceExtractor()


# 1. 获取国家/地区列表
@router.get("/countries", response_model=CountriesResponse)
async def get_countries():
    """返回 MongoDB 中所有可用的国家/地区选项"""
    try:
        collection = get_market_knowledge_collection()
        cursor = collection.find({}, {"_id": 0, "country_code": 1, "country_name": 1, "region": 1, "target_language": 1})
        docs = await cursor.to_list(length=100)
        countries = [
            CountryOption(
                country_code=d["country_code"],
                country_name=d.get("country_name", d["country_code"]),
                region=d.get("region", ""),
                target_language=d.get("target_language", "English"),
            )
            for d in docs
        ]
        return CountriesResponse(countries=countries)
    except Exception as e:
        logger.error(f"获取国家列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取国家列表失败: {str(e)}")


# 2. 生成产品简介
@router.post("/generate-intro", response_model=GenerateIntroResponse)
async def generate_intro(request: GenerateIntroRequest):
    """
    生成产品简介
    - intro_length 可选 short / medium / long
    """
    try:
        product_info = request.product_info
        if not product_info.title.strip():
            return GenerateIntroResponse(success=False, error="产品名称不能为空")
        key_features = feature_extractor.extract_key_features(product_info)
        prompt = prompt_builder.build_intro_prompt(
            key_features=key_features,
            product_info=product_info.model_dump(),
            market_info=request.market_info.model_dump(),
            intro_length=request.intro_length,
        )
        prompt = await localization_adapter.adapt_prompt(
            prompt=prompt,
            country=request.market_info.country,
            target_language=request.market_info.target_language,
        )
        product_intro = await llm_client.generate_text_async(prompt)
        if product_intro:
            return GenerateIntroResponse(
                success=True,
                key_features=key_features,
                product_intro=product_intro.strip(),
            )
        else:
            return GenerateIntroResponse(success=False, error="LLM未返回有效简介内容")
    except ValueError as e:
        return GenerateIntroResponse(success=False, error=f"参数错误：{str(e)}")
    except Exception as e:
        logger.error(f"生成简介异常: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误：{str(e)}")


# 3. AI提取消费者偏好并存入数据库
@router.post("/extract-preferences", response_model=ExtractPreferencesResponse)
async def extract_preferences(request: ExtractPreferencesRequest):
    """使用独立AI从数据集文本中自动识别国家并提取消费者偏好，结果存入 MongoDB。"""
    if not request.dataset_text.strip():
        raise HTTPException(status_code=400, detail="数据集内容不能为空")
    result = await preference_extractor.extract_and_save(
        dataset_text=request.dataset_text,
        country_code=request.country_code,
    )
    if result.get("success"):
        return ExtractPreferencesResponse(success=True, data=result.get("data"))
    else:
        return ExtractPreferencesResponse(
            success=False,
            country_not_found=result.get("country_not_found", False),
            error=result.get("error", "未知错误"),
        )


# 4. 上传数据集文件（CSV / TXT / JSON）
@router.post("/upload-dataset", response_model=UploadDatasetResponse)
async def upload_dataset(file: UploadFile = File(...)):
    """
    上传数据集文件（.txt / .csv / .json），解码并返回全文及预览。
    前端取得 full_text 后，连同国家代码提交给 /extract-preferences 进行AI分析。
    """
    fname = file.filename or ""
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext not in {"txt", "csv", "json"}:
        return UploadDatasetResponse(success=False, error="仅支持 .txt / .csv / .json 文件")
    try:
        raw_bytes = await file.read()
        if len(raw_bytes) == 0:
            return UploadDatasetResponse(success=False, error="文件内容为空")
        detected = chardet.detect(raw_bytes)
        encoding = detected.get("encoding") or "utf-8"
        try:
            text = raw_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            text = raw_bytes.decode("utf-8", errors="replace")
        return UploadDatasetResponse(
            success=True,
            filename=fname,
            text_preview=text[:200],
            char_count=len(text),
            full_text=text,
            lang="ru" if sum(1 for c in text[:2000] if '\u0400' <= c <= '\u04FF') / max(len(text[:2000]), 1) > 0.2 else "en",
        )
    except Exception as e:
        logger.error(f"上传数据集失败: {e}")
        return UploadDatasetResponse(success=False, error=f"文件处理异常：{str(e)}")
