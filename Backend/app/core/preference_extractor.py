import os
import json
import re
import logging
import httpx
from typing import Optional
from dotenv import load_dotenv
from app.core.database import get_market_knowledge_collection

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, "server.env")
load_dotenv(dotenv_path=ENV_PATH)


class PreferenceExtractor:
    """
    使用独立AI从产品/市场数据集中提取消费者偏好，
    支持手动指定国家或由AI自动识别，将结果按知识库格式保存到 market_knowledge 集合。
    """

    def __init__(self):
        self.api_key = os.getenv("PREF_API_KEY")
        self.base_url = os.getenv("PREF_API_BASE_URL")
        self.model_endpoint = os.getenv("PREF_MODEL_ENDPOINT")

    async def _call_ai(self, prompt: str) -> Optional[str]:
        """异步调用偏好提取AI"""
        if not all([self.api_key, self.base_url, self.model_endpoint]):
            logger.error("偏好提取AI配置不完整，请检查 server.env")
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_endpoint,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1200,
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(self.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            logger.error(f"偏好提取AI HTTP错误: {e.response.status_code} {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"偏好提取AI调用失败: {type(e).__name__}: {e}")
            return None

    async def extract_and_save(self, dataset_text: str, country_code: Optional[str] = None) -> dict:
        """
        从数据集文本中提取消费者偏好，按知识库格式存入 market_knowledge 集合。
        :param dataset_text: 原始数据集内容
        :param country_code: 可选，手动指定国家代码；为 None 时由 AI 自动识别
        :return: 提取结果摘要
        """
        if country_code:
            country_hint = (
                f"注意：本数据集来源国家已确认为 [{country_code.upper()}]，"
                f"请直接使用该国家代码，无需重新判断。"
            )
        else:
            country_hint = (
                "请根据数据集内容、语言、货币、品牌、地名等线索判断目标市场国家。"
                "若完全无法判断，将 country_code 设为 null。"
            )

        prompt = f"""你是跨境电商消费者行为分析专家。
请对以下数据集进行分析，并按照指定的知识库格式输出结构化结果。

{country_hint}

数据集内容（前3000字）：
{dataset_text[:3000]}

要求：
- country_code 使用大写英文代码，与以下示例保持一致：USA、JAPAN、GERMANY、UK、FRANCE、BRAZIL、INDIA、SOUTH_KOREA、AUSTRALIA、CANADA、MEXICO、SAUDI_ARABIA。
- 如果完全无法判断国家/地区信息，请将 country_code 设为 null。
- region 使用中文，如：北美、欧洲、东亚、南亚、中东、南美、拉丁美洲、大洋洲。
- target_language 使用英文语言名，如：English、Japanese、German、French、Portuguese、Spanish、Korean、Arabic。
- preferences、taboos、language_style 均为简洁中文描述，每项不超过30字，干练明了，避免冗长。
- 仅返回纯 JSON，无其他文字。

返回格式（严格与知识库字段一致）：
{{
  "country_code": "国家代码或null",
  "country_name": "国家中文名",
  "region": "所属地区",
  "target_language": "目标语言",
  "preferences": "消费者偏好描述",
  "taboos": "文化禁忌描述",
  "language_style": "适合该市场的语言风格"
}}"""

        raw = await self._call_ai(prompt)
        if not raw:
            return {"success": False, "error": "AI未返回有效内容"}

        try:
            cleaned = re.sub(r"```json|```", "", raw).strip()
            preference_data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(f"偏好AI返回内容无法解析为JSON: {raw[:200]}")
            return {"success": False, "error": "AI返回格式错误，无法解析"}

        # 检查是否识别到国家
        detected_code = preference_data.get("country_code")
        if not detected_code or str(detected_code).lower() == "null":
            return {
                "success": False,
                "country_not_found": True,
                "error": "数据集中未能识别到有效的国家/地区信息，请检查数据集内容后重试",
            }

        detected_code = detected_code.upper()
        preference_data["country_code"] = detected_code

        # 按知识库格式写入 market_knowledge（upsert by country_code）
        mk_collection = get_market_knowledge_collection()
        mk_update = {}
        for field in ["country_name", "region", "target_language",
                      "preferences", "taboos", "language_style"]:
            if field in preference_data and preference_data[field]:
                mk_update[field] = preference_data[field]

        if mk_update:
            await mk_collection.update_one(
                {"country_code": detected_code},
                {"$set": mk_update},
                upsert=True,
            )

        logger.info(f"已将 {detected_code} 消费者偏好按知识库格式写入 market_knowledge")
        return {"success": True, "data": preference_data}
