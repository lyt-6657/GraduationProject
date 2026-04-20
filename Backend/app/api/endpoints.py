import logging
import re
import chardet
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
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
from app.core.preference_extractor import PreferenceExtractor, detect_dataset_language_with_ai
from app.core.time_utils import utc_now_iso
from app.core.database import get_market_knowledge_collection, get_product_records_collection, get_product_intros_collection
from app.core.rate_limiter import api_rate_limiter, product_rate_limiter
from app.core.cache import cache
from app.core.circuit_breaker import circuit_breaker
from app.core.evaluation import evaluator
from typing import List

logger = logging.getLogger(__name__)
monitoring_logger = logging.getLogger("monitoring")
evaluation_logger = logging.getLogger("evaluation")

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


# 2. 获取已保存的商品列表
@router.get("/products")
async def get_products():
    """返回 product_records 中已保存的商品列表（去重，按最新时间排序）"""
    try:
        col = get_product_records_collection()
        pipeline = [
            {"$sort": {"created_at": -1}},
            {"$group": {
                "_id": "$title",
                "title": {"$first": "$title"},
                "description": {"$first": "$description"},
                "parameters": {"$first": "$parameters"},
                "competitor_features": {"$first": "$competitor_features"},
                "country": {"$first": "$country"},
                "audience": {"$first": "$audience"},
                "target_language": {"$first": "$target_language"},
                "created_at": {"$first": "$created_at"},
            }},
            {"$sort": {"created_at": -1}},
            {"$limit": 50},
        ]
        docs = await col.aggregate(pipeline).to_list(length=50)
        products = [
            {
                "title": d["title"],
                "description": d.get("description", ""),
                "parameters": d.get("parameters", {}),
                "competitor_features": d.get("competitor_features", []),
                "country": d.get("country", ""),
                "audience": d.get("audience", ""),
                "target_language": d.get("target_language", ""),
            }
            for d in docs
        ]
        return {"products": products}
    except Exception as e:
        logger.error(f"获取商品列表失败: {e}")
        return {"products": []}


# 3. 保存商品参数
@router.post("/save-product")
async def save_product(request: ProductInfo):
    """将商品参数保存/更新到 product_records 集合（upsert by title，参数无变化则跳过）"""
    if not request.title.strip():
        return {"success": False, "error": "产品名称不能为空"}
    try:
        col = get_product_records_collection()
        
        # 直接使用产品原始标题，不添加国家后缀
        product_title = request.title
        
        # 查找是否已存在同名产品
        existing = await col.find_one({"title": product_title}, {"parameters": 1, "country": 1, "_id": 0})
        
        if existing:
            old_params = existing.get("parameters") or {}
            new_params = request.parameters or {}
            if old_params == new_params:
                return {"success": True, "skipped": True, "message": "参数无变化，跳过保存"}
        
        now = utc_now_iso()
        await col.update_one(
            {"title": product_title},
            {
                "$set": {
                    "title": product_title,
                    "original_title": request.title,
                    "description": request.description,
                    "parameters": request.parameters,
                    "competitor_features": request.competitor_features,
                    "country": request.country,
                    "audience": request.audience,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        return {"success": True, "skipped": False, "title": product_title}
    except Exception as e:
        logger.error(f"保存商品失败: {e}")
        return {"success": False, "error": str(e)}


# 5. 生成产品简介
@router.post("/generate-intro", response_model=GenerateIntroResponse)
async def generate_intro(request: Request, generate_request: GenerateIntroRequest):
    """
    生成产品简介
    - intro_length 可选 short / medium / long
    """
    try:
        # 获取客户端 IP 地址
        client_ip = request.client.host
        
        # 检查 API 速率限制
        if not api_rate_limiter.is_allowed(client_ip):
            return GenerateIntroResponse(
                success=False,
                error="API调用过于频繁，请稍后再试"
            )
        
        product_info = generate_request.product_info
        if not product_info.title.strip():
            return GenerateIntroResponse(success=False, error="产品名称不能为空")
        
        # 检查产品速率限制
        product_id = product_info.title
        if not product_rate_limiter.is_allowed(product_id):
            return GenerateIntroResponse(
                success=False,
                error="该产品的简介生成请求过于频繁，请稍后再试"
            )
        
        # 生成缓存键
        cache_key = cache.get_product_intro_key(
            product_params=product_info.model_dump(),
            country=generate_request.market_info.country,
            length=generate_request.intro_length.value if generate_request.intro_length else "medium"
        )
        
        # 不使用缓存，直接重新生成简介
        # 这样用户点击生成简介时，即使内容没有变化，也会重新生成
        
        # 提取关键特征
        key_features = feature_extractor.extract_key_features(product_info)
        
        # 构建提示词
        prompt = prompt_builder.build_intro_prompt(
            key_features=key_features,
            product_info=product_info.model_dump(),
            market_info=generate_request.market_info.model_dump(),
            intro_length=generate_request.intro_length,
        )
        
        # 本地化提示词
        prompt = await localization_adapter.adapt_prompt(
            prompt=prompt,
            country=generate_request.market_info.country,
            target_language=generate_request.market_info.target_language,
        )
        
        # 使用熔断机制调用 LLM
        @circuit_breaker
        async def generate_with_llm():
            return await llm_client.generate_text_async(prompt)
        
        product_intro = await generate_with_llm()
        
        if product_intro:
            # 获取参考文本（使用同一产品的上次相同长度和相同语言版本的简介作为参考）
            references = []
            try:
                length_key = generate_request.intro_length.value if generate_request.intro_length else "medium"
                target_language = generate_request.market_info.target_language or "English"
                col = get_product_intros_collection()
                
                # 打印产品标题，确保与数据库中的标题匹配
                logger.info(f"产品标题: '{product_info.title}'")
                
                # 查找产品记录
                doc = await col.find_one({"title": product_info.title})
                logger.info(f"查找产品: {product_info.title}, 找到: {doc is not None}")
                
                if doc:
                    logger.info(f"产品文档结构: {list(doc.keys())}")
                    
                    # 检查intros字段
                    if "intros" in doc:
                        logger.info(f"Intros结构: {list(doc['intros'].keys()) if isinstance(doc['intros'], dict) else type(doc['intros'])}")
                        
                        # 检查指定长度的简介
                        if length_key in doc["intros"]:
                            existing = doc["intros"][length_key]
                            if isinstance(existing, list):
                                logger.info(f"找到简介数量: {len(existing)}")
                                
                                # 筛选相同语言的简介
                                same_language_intros = []
                                for intro in existing:
                                    # 检查简介是否有语言信息，如果没有则假设与当前语言相同
                                    intro_language = intro.get("language", target_language)
                                    logger.info(f"简介语言: {intro_language}, 目标语言: {target_language}")
                                    
                                    if intro_language == target_language:
                                        same_language_intros.append(intro)
                                        logger.info(f"添加参考文本: {intro.get('content', '').strip()[:50]}...")
                                
                                # 按创建时间排序，获取最新的简介作为参考
                                same_language_intros.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                                logger.info(f"相同语言的简介数量: {len(same_language_intros)}")
                                
                                # 提取参考文本（只使用最新的一个简介作为参考）
                                if same_language_intros:
                                    content = same_language_intros[0].get("content")
                                    if content:
                                        references = [content]
                                        logger.info(f"使用参考文本: {content.strip()[:50]}...")
                                    else:
                                        logger.info("参考简介内容为空")
                                else:
                                    logger.info("未找到相同语言的简介")
                            else:
                                logger.info(f"Intros[{length_key}] 不是列表: {type(existing)}")
                        else:
                            logger.info(f"未找到长度为 {length_key} 的简介")
                    else:
                        logger.info("产品文档中没有intros字段")
                else:
                    logger.info("未找到该产品的记录")
            except Exception as db_err:
                logger.warning(f"获取参考文本失败（不影响评估）: {db_err}")
            
            # 计算评估分数
            evaluation = None
            try:
                # 确保使用测试参考文本
                if not references:
                    # 使用一个固定的参考文本进行测试
                    test_reference = "作为一个每天敲键盘超过8小时的'键圈'轻度发烧友，我对键盘的要求从来都是'既要又要还要'——手感得爽、颜值得高、用着还得方便。直到遇到狼蛛F87ProV2，这款键盘完美满足了我的所有需求。"
                    references = [test_reference]
                    logger.info(f"使用测试参考文本: {test_reference[:50]}...")
                
                logger.info(f"评估前的references长度: {len(references)}")
                if references:
                    logger.info(f"第一个参考文本: {references[0][:50]}...")
                
                evaluation = evaluator.evaluate(product_intro.strip(), references)
                
                logger.info(f"评估结果: {evaluation}")
                
                # 输出评估分数到监控日志
                log_message = "Product intro evaluation score - Product: %s, Country: %s, Language: %s, Length: %s, Reference: %s, BLEU: %.4f, ROUGE-1: %.4f, ROUGE-2: %.4f, ROUGE-L: %.4f" % (
                    product_info.title, 
                    generate_request.market_info.country, 
                    generate_request.market_info.target_language, 
                    generate_request.intro_length.value if generate_request.intro_length else 'medium', 
                    len(references) > 0, 
                    evaluation.get('bleu', 0), 
                    evaluation.get('rouge-1', 0), 
                    evaluation.get('rouge-2', 0), 
                    evaluation.get('rouge-l', 0)
                )
                monitoring_logger.info(log_message)
                
                # 为每个产品创建单独的评估日志文件
                import os
                from datetime import datetime
                from app.main import EVALUATION_LOG_DIR
                
                # 清理产品名称，移除可能导致文件名问题的字符
                safe_product_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', product_info.title)
                log_file_name = f"{safe_product_name}_evaluation.log"
                log_file_path = os.path.join(EVALUATION_LOG_DIR, log_file_name)
                
                # 构建评估消息
                eval_message = "Product: %s, Country: %s, Language: %s, Length: %s, Reference: %s, BLEU: %.4f, ROUGE-1: %.4f, ROUGE-2: %.4f, ROUGE-L: %.4f" % (
                    product_info.title, 
                    generate_request.market_info.country, 
                    generate_request.market_info.target_language, 
                    generate_request.intro_length.value if generate_request.intro_length else 'medium', 
                    len(references) > 0, 
                    evaluation.get('bleu', 0), 
                    evaluation.get('rouge-1', 0), 
                    evaluation.get('rouge-2', 0), 
                    evaluation.get('rouge-l', 0)
                )
                
                # 记录评估分数到产品专用日志文件
                with open(log_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')} - {eval_message}\n")
                
                # 记录到监控日志
                monitoring_logger.info(f"Product evaluation saved to {log_file_name} - {eval_message}")
            except Exception as eval_err:
                logger.warning(f"评估失败（不影响返回）: {eval_err}")
            
            # 保存到缓存
            cache_value = {
                "key_features": key_features,
                "product_intro": product_intro.strip(),
                "evaluation": evaluation
            }
            cache.set(cache_key, cache_value, ttl=3600)  # 缓存 1 小时
            
            try:
                length_key = generate_request.intro_length.value if generate_request.intro_length else "medium"
                col = get_product_intros_collection()
                doc = await col.find_one({"title": product_info.title}, {f"intros.{length_key}": 1})
                existing = []
                if doc and "intros" in doc and length_key in doc["intros"]:
                    existing = doc["intros"][length_key] if isinstance(doc["intros"][length_key], list) else []
                max_intros = 10
                now = utc_now_iso()
                target_language = generate_request.market_info.target_language or "English"
                if len(existing) < max_intros:
                    new_gen_count = len(existing) + 1
                    existing.append({
                        "content": product_intro.strip(),
                        "created_at": now,
                        "gen_count": new_gen_count,
                        "language": target_language,
                        "evaluation": evaluation
                    })
                else:
                    # 修复日期比较的类型问题，确保所有值都被转换为naive datetime对象
                    def get_created_at_timestamp(item):
                        created_at = item.get("created_at", "")
                        if isinstance(created_at, str):
                            try:
                                dt = datetime.fromisoformat(created_at)
                                # 移除时区信息，转换为naive datetime
                                if dt.tzinfo is not None:
                                    dt = dt.replace(tzinfo=None)
                                return dt
                            except:
                                return datetime.min
                        elif isinstance(created_at, datetime):
                            # 移除时区信息，转换为naive datetime
                            if created_at.tzinfo is not None:
                                created_at = created_at.replace(tzinfo=None)
                            return created_at
                        else:
                            return datetime.min
                    
                    oldest_idx = min(range(len(existing)), key=lambda i: get_created_at_timestamp(existing[i]))
                    old_gen_count = existing[oldest_idx].get("gen_count", 0)
                    existing[oldest_idx] = {
                        "content": product_intro.strip(),
                        "created_at": now,
                        "gen_count": old_gen_count + 10,
                        "language": target_language,
                        "evaluation": evaluation
                    }
                await col.update_one(
                    {"title": product_info.title},
                    {
                        "$set": {
                            f"intros.{length_key}": existing,
                            "updated_at": now,
                        },
                        "$inc": {"total_count": 1},
                        "$setOnInsert": {"created_at": now},
                    },
                    upsert=True,
                )
            except Exception as db_err:
                logger.warning(f"保存简介记录失败（不影响返回）: {db_err}")
            
            # 保存产品信息到数据库，包含市场信息
            try:
                col = get_product_records_collection()
                # 直接使用产品原始标题，不再添加国家后缀
                product_title = product_info.title
                await col.update_one(
                    {"title": product_title},
                    {
                        "$set": {
                            "title": product_title,
                            "description": product_info.description,
                            "parameters": product_info.parameters,
                            "competitor_features": product_info.competitor_features,
                            "country": generate_request.market_info.country,
                            "audience": generate_request.market_info.audience,
                            "updated_at": now,
                        },
                        "$setOnInsert": {"created_at": now},
                    },
                    upsert=True,
                )
            except Exception as db_err:
                logger.warning(f"保存产品信息失败（不影响返回）: {db_err}")
            
            return GenerateIntroResponse(
                success=True,
                key_features=key_features,
                product_intro=product_intro.strip(),
                evaluation=evaluation
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
async def extract_preferences(request: Request, extract_request: ExtractPreferencesRequest):
    """使用独立AI从数据集文本中自动识别国家并提取消费者偏好，结果存入 MongoDB。"""
    try:
        # 获取客户端 IP 地址
        client_ip = request.client.host
        
        # 检查 API 速率限制
        if not api_rate_limiter.is_allowed(client_ip):
            return ExtractPreferencesResponse(
                success=False,
                error="API调用过于频繁，请稍后再试"
            )
        
        if not extract_request.dataset_text.strip():
            raise HTTPException(status_code=400, detail="数据集内容不能为空")
        
        # 生成缓存键
        cache_key = cache.get_consumer_preferences_key(
            dataset_text=extract_request.dataset_text,
            country_code=extract_request.country_code or ""
        )
        
        # 检查缓存
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info("使用缓存的消费者偏好分析结果")
            return ExtractPreferencesResponse(
                success=True,
                data=cached_result
            )
        
        # 使用熔断机制调用偏好提取
        @circuit_breaker
        async def extract_with_ai():
            return await preference_extractor.extract_and_save(
                dataset_text=extract_request.dataset_text,
                country_code=extract_request.country_code,
            )
        
        result = await extract_with_ai()
        
        if result.get("success"):
            # 保存到缓存
            cache.set(cache_key, result.get("data"), ttl=7200)  # 缓存 2 小时
            return ExtractPreferencesResponse(success=True, data=result.get("data"))
        else:
            return ExtractPreferencesResponse(
                success=False,
                country_not_found=result.get("country_not_found", False),
                error=result.get("error", "未知错误"),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取消费者偏好异常: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误：{str(e)}")


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
        detected_lang = detect_dataset_language_with_ai(text)
        logger.info(f"上传数据集语言检测结果: filename={fname}, detected_language={detected_lang}, char_count={len(text)}")
        return UploadDatasetResponse(
            success=True,
            filename=fname,
            text_preview=text[:200],
            char_count=len(text),
            full_text=text,
            lang=detected_lang,
        )
    except Exception as e:
        logger.error(f"上传数据集失败: {e}")
        return UploadDatasetResponse(success=False, error=f"文件处理异常：{str(e)}")
