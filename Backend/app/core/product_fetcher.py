from typing import Dict, Optional
from app.core.llm_client import LLMClient

class ProductInfoFetcher:
    def __init__(self):
        self.llm_client = LLMClient()

    def fetch_product_info(self, product_name: str) -> Optional[Dict]:
        """
        基于产品名自动获取产品核心信息
        :param product_name: 产品名称（如：无线蓝牙耳机）
        :return: 包含描述、参数、核心卖点的字典
        """
        prompt = f"""
请基于以下产品名称，生成该产品的核心信息，返回JSON格式，要求：
1. description：详细描述（100字左右）
2. parameters：核心参数（至少3个）
3. key_features：核心卖点（至少4个）
4. competitor_features：典型竞品的劣势（至少3个）

产品名称：{product_name}

仅返回JSON，不要多余内容，示例：
{{
    "description": "这款无线蓝牙耳机采用蓝牙5.3技术，续航30小时，IPX7防水，支持主动降噪，佩戴舒适",
    "parameters": {{"材质":"硅胶+ABS","续航":"30小时","防水等级":"IPX7"}},
    "key_features": ["蓝牙5.3技术", "30小时续航", "IPX7防水", "主动降噪"],
    "competitor_features": ["续航仅20小时", "无降噪功能", "防水等级IPX5"]
}}
        """.strip()

        # 调用LLM生成信息
        raw_response = self.llm_client.generate_text(prompt, temperature=0.5)
        if not raw_response:
            return None

        # 解析JSON结果
        try:
            import json
            return json.loads(raw_response)
        except Exception as e:
            print(f"解析产品信息失败: {e}")
            return None