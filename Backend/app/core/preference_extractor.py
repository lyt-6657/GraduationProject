import os
import json
import re
import logging
import httpx
from datetime import datetime
from typing import Optional
from collections import Counter
from dotenv import load_dotenv
from app.core.database import get_market_knowledge_collection

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, "server.env")
load_dotenv(dotenv_path=ENV_PATH)

# ── 自动检测 GPU ──
try:
    import torch
    _DEVICE = 0 if torch.cuda.is_available() else -1
except ImportError:
    _DEVICE = -1
_DEVICE_NAME = "GPU" if _DEVICE == 0 else "CPU"

# ── 懒加载本地模型 ──
_english_model = None
_russian_model = None


def _get_english_model():
    global _english_model
    if _english_model is None:
        import warnings
        warnings.filterwarnings("ignore")
        from transformers import pipeline
        logger.info(f"加载英语模型，设备：{_DEVICE_NAME}")
        _english_model = pipeline(
            "text-classification",
            model="nlptown/bert-base-multilingual-uncased-sentiment",
            truncation=True,
            max_length=512,
            device=_DEVICE,
            batch_size=32,
        )
    return _english_model


def _get_russian_model():
    global _russian_model
    if _russian_model is None:
        import warnings
        warnings.filterwarnings("ignore")
        from transformers import pipeline
        logger.info(f"加载俄语模型，设备：{_DEVICE_NAME}")
        _russian_model = pipeline(
            "text-classification",
            model="seara/rubert-tiny2-russian-sentiment",
            truncation=True,
            max_length=512,
            device=_DEVICE,
            batch_size=32,
        )
    return _russian_model


# ── 偏好/禁忌关键词词典 ──
PREFERENCE_EN = [
    "quality", "durable", "material", "soft", "beautiful",
    "fast delivery", "packaging", "price", "size", "fit",
    "color", "design", "comfortable", "easy to use",
]
TABOO_EN = [
    "too small", "too big", "uncomfortable", "fragile",
    "broken", "bad quality", "ugly", "wrong color", "offensive",
]
PREFERENCE_RU = [
    "качество", "прочный", "материал", "мягкий", "удобный",
    "быстрая доставка", "упаковка", "цена", "размер", "цвет",
]
TABOO_RU = [
    "слишком маленький", "слишком большой", "неудобный",
    "хрупкий", "сломан", "плохое качество", "некрасивый",
]


def _detect_lang(text: str) -> str:
    """简单语言检测：俄语字符占比超过20%则判定为俄语，否则英语。"""
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    return "ru" if cyrillic / max(len(text), 1) > 0.2 else "en"


def _analyze_reviews_local(dataset_text: str) -> dict:
    """
    用本地 BERT 模型批量分析评论，统计高频偏好和禁忌。
    - 关键词匹配在全文上直接统计，无需逐行调用模型
    - 情感分析使用批量推理（batch_size=32），自动使用 GPU（如可用）
    返回：{lang, top_preferences, top_taboos, positive_ratio, sample}
    """
    lines = [l.strip() for l in dataset_text.splitlines() if l.strip()]
    if not lines:
        return {"lang": "en", "top_preferences": [], "top_taboos": [], "positive_ratio": 0}

    lang = _detect_lang(dataset_text)
    model = _get_russian_model() if lang == "ru" else _get_english_model()
    pref_kw = PREFERENCE_RU if lang == "ru" else PREFERENCE_EN
    taboo_kw = TABOO_RU if lang == "ru" else TABOO_EN

    # 关键词匹配直接在全文统计（不需要模型，速度极快）
    full_text_lower = dataset_text.lower()
    pref_counts = Counter({w: full_text_lower.count(w) for w in pref_kw if w in full_text_lower})
    taboo_counts = Counter({w: full_text_lower.count(w) for w in taboo_kw if w in full_text_lower})

    # 批量情感推理：取前100行，每条限500字符
    batch = [l[:500] for l in lines[:100]]
    positive = 0
    try:
        results = model(batch)  # pipeline 自动按 batch_size 分批推理
        for r in results:
            if any(s in r["label"].upper() for s in ["4", "5", "POS", "POSITIVE"]):
                positive += 1
    except Exception as e:
        logger.warning(f"批量推理失败，回退逐条: {e}")
        for text in batch:
            try:
                r = model(text)[0]
                if any(s in r["label"].upper() for s in ["4", "5", "POS", "POSITIVE"]):
                    positive += 1
            except Exception:
                continue

    total = len(batch)
    ratio = round(positive / max(total, 1), 2)
    logger.info(f"本地模型分析完成：{total}条，设备={_DEVICE_NAME}，正面率={ratio}")

    return {
        "lang": lang,
        "top_preferences": [w for w, _ in pref_counts.most_common(8)],
        "top_taboos": [w for w, _ in taboo_counts.most_common(5)],
        "positive_ratio": ratio,
        "sample": dataset_text[:1000],
    }


class PreferenceExtractor:
    """
    两阶段分析：
    1. 本地 BERT 模型（英语/俄语）批量推理 + 全文关键词统计
    2. PREF AI 将结果翻译整合为中文知识库格式
    最终结果保存到 market_knowledge 集合。
    """

    def __init__(self):
        self.api_key = os.getenv("PREF_API_KEY")
        self.base_url = os.getenv("PREF_API_BASE_URL")
        self.model_endpoint = os.getenv("PREF_MODEL_ENDPOINT")

    async def _call_ai(self, prompt: str) -> Optional[str]:
        """异步调用 PREF AI"""
        if not all([self.api_key, self.base_url, self.model_endpoint]):
            logger.error("偏好提取AI配置不完整，请检查 server.env")
            return None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model_endpoint,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 800,
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(self.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            logger.error(f"PREF AI HTTP错误: {e.response.status_code} {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"PREF AI调用失败: {type(e).__name__}: {e}")
            return None

    async def extract_and_save(self, dataset_text: str, country_code: Optional[str] = None) -> dict:
        """
        两阶段分析数据集，结果按知识库格式存入 market_knowledge。
        :param dataset_text: 原始数据集内容
        :param country_code: 可选，手动指定国家代码；为 None 时由 AI 自动识别
        """
        # ── 阶段一：本地 BERT 模型批量分析 ──
        logger.info("阶段一：启动本地 BERT 模型分析...")
        local_result = _analyze_reviews_local(dataset_text)
        lang = local_result["lang"]
        top_prefs = local_result["top_preferences"]
        top_taboos = local_result["top_taboos"]
        positive_ratio = local_result["positive_ratio"]
        logger.info(f"本地分析完成：lang={lang}, 正面率={positive_ratio}, 偏好={top_prefs}, 禁忌={top_taboos}")

        # ── 阶段二：PREF AI 翻译 + 整合 ──
        if country_code:
            country_hint = f"数据集来源国家已确认为 [{country_code.upper()}]，请直接使用该国家代码。"
        else:
            country_hint = "请根据评论语言、内容、品牌、地名等线索判断目标市场国家，若无法判断则将 country_code 设为 null。"

        prompt = f"""你是跨境电商消费者行为分析专家。
以下是由本地AI模型（{'俄语' if lang == 'ru' else '英语'}评论分析）提取的消费者偏好数据，请将其翻译为中文并整合为知识库格式。

{country_hint}

本地模型分析结果：
- 评论语言：{'俄语' if lang == 'ru' else '英语'}
- 正面评价占比：{positive_ratio * 100:.0f}%
- 高频偏好关键词（原文）：{', '.join(top_prefs) if top_prefs else '无'}
- 高频禁忌关键词（原文）：{', '.join(top_taboos) if top_taboos else '无'}

数据集样本（前1000字）：
{local_result.get('sample', dataset_text[:1000])}

要求：
- country_code 使用大写英文代码：USA、JAPAN、GERMANY、UK、FRANCE、BRAZIL、INDIA、SOUTH_KOREA、AUSTRALIA、CANADA、MEXICO、SAUDI_ARABIA、RUSSIA 等。
- region 使用中文：北美、欧洲、东亚、南亚、中东、南美、拉丁美洲、大洋洲、东欧 等。
- target_language 使用英文：English、Japanese、German、French、Portuguese、Spanish、Korean、Arabic、Russian 等。
- preferences、taboos、language_style 用简洁中文描述，每项不超过30字，干练明了。
- 所有字段值必须为中文（country_code 和 target_language 除外）。
- 仅返回纯 JSON，无其他文字。

返回格式：
{{
  "country_code": "国家代码或null",
  "country_name": "国家中文名",
  "region": "所属地区",
  "target_language": "目标语言",
  "preferences": "消费者偏好（中文，不超过30字）",
  "taboos": "文化禁忌（中文，不超过30字）",
  "language_style": "语言风格（中文，不超过30字）"
}}"""

        logger.info("阶段二：调用 PREF AI 进行翻译整合...")
        raw = await self._call_ai(prompt)
        if not raw:
            return {"success": False, "error": "PREF AI未返回有效内容"}

        try:
            cleaned = re.sub(r"```json|```", "", raw).strip()
            preference_data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(f"PREF AI返回内容无法解析为JSON: {raw[:200]}")
            return {"success": False, "error": "AI返回格式错误，无法解析"}

        detected_code = preference_data.get("country_code")
        if not detected_code or str(detected_code).lower() == "null":
            return {
                "success": False,
                "country_not_found": True,
                "error": "数据集中未能识别到有效的国家/地区信息，请检查数据集内容后重试",
            }

        detected_code = detected_code.upper()
        preference_data["country_code"] = detected_code

        # 保存到 market_knowledge（upsert by country_code）
        mk_collection = get_market_knowledge_collection()
        mk_update = {}
        for field in ["country_name", "region", "target_language",
                      "preferences", "taboos", "language_style"]:
            if field in preference_data and preference_data[field]:
                mk_update[field] = preference_data[field]

        # 添加创建时间和更新时间
        current_time = datetime.now()
        mk_update["updated_at"] = current_time

        if mk_update:
            await mk_collection.update_one(
                {"country_code": detected_code},
                {
                    "$set": mk_update,
                    "$setOnInsert": {"created_at": current_time}
                },
                upsert=True,
            )

        logger.info(f"已将 {detected_code} 消费者偏好写入 market_knowledge")
        return {"success": True, "data": preference_data}


def detect_dataset_language_with_ai(dataset_text: str) -> str:
    """
    检测数据集的语言
    :param dataset_text: 数据集文本
    :return: 语言代码，如 "en"、"ru" 等
    """
    # 使用现有的语言检测函数
    return _detect_lang(dataset_text)


def log_local_model_config():
    """
    记录本地模型配置信息
    """
    global _DEVICE, _DEVICE_NAME
    logger.info(f"本地模型配置: 设备={_DEVICE_NAME}, 设备ID={_DEVICE}")
    logger.info(f"英语模型: nlptown/bert-base-multilingual-uncased-sentiment")
    logger.info(f"俄语模型: seara/rubert-tiny2-russian-sentiment")