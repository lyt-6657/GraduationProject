import os
import requests
from dotenv import load_dotenv
from typing import Optional, Dict

# 加载环境变量
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, "server.env")
load_dotenv(dotenv_path=ENV_PATH)

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("ARK_API_KEY")
        self.base_url = os.getenv("ARK_API_BASE_URL")
        self.model_endpoint = os.getenv("ARK_MODEL_ENDPOINT")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def generate_text(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """
        调用火山方舟API生成文本
        :param prompt: 提示词
        :param temperature: 生成温度，值越高越随机
        :return: 生成的文本，失败返回None
        """
        if not all([self.api_key, self.base_url, self.model_endpoint]):
            print("LLM配置不完整，请检查.env文件")
            return None

        payload = {
            "model": self.model_endpoint,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 500  # 控制生成文本长度
        }

        try:
            response = requests.post(
                url=self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()  # 抛出HTTP错误
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except requests.exceptions.RequestException as e:
            print(f"调用LLM API失败: {str(e)}")
            return None