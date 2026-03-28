import os
import logging
import httpx
from dotenv import load_dotenv
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, "server.env")
load_dotenv(dotenv_path=ENV_PATH)


class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("ARK_API_KEY")
        self.base_url = os.getenv("ARK_API_BASE_URL")
        self.model_endpoint = os.getenv("ARK_MODEL_ENDPOINT")

    def _build_payload(self, prompt: str, temperature: float, max_tokens: int) -> dict:
        return {
            "model": self.model_endpoint,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    def _resolve_max_tokens(self, prompt: str) -> int:
        """根据提示词长度动态决定 max_tokens，详细版给更多空间"""
        prompt_len = len(prompt)
        if prompt_len > 2000:
            return 4096
        if prompt_len > 1000:
            return 2048
        return 2048

    def generate_text(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """同步调用火山方舟API生成文本"""
        if not all([self.api_key, self.base_url, self.model_endpoint]):
            logger.error("LLM配置不完整，请检查server.env")
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(prompt, temperature, self._resolve_max_tokens(prompt))
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            logger.info(f"LLM生成成功，返回长度: {len(content)}")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API HTTP错误: {e.response.status_code} {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"LLM API调用异常: {type(e).__name__}: {e}")
            return None

    async def generate_text_async(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """异步调用火山方舟API生成文本"""
        if not all([self.api_key, self.base_url, self.model_endpoint]):
            logger.error("LLM配置不完整，请检查server.env")
            return None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(prompt, temperature, self._resolve_max_tokens(prompt))
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            logger.info(f"LLM生成成功，返回长度: {len(content)}")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API HTTP错误: {e.response.status_code} {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"LLM API调用异常: {type(e).__name__}: {e}")
            return None
