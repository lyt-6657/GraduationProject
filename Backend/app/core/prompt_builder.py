import random
from app.models.schemas import IntroLength

# 各长度对应的目标字数范围
LENGTH_CONFIG = {
    IntroLength.short:  {"label": "短",  "min": 80,  "max": 120},
    IntroLength.medium: {"label": "中",  "min": 250, "max": 350},
    IntroLength.long:   {"label": "长",  "min": 450, "max": 550},
}

# 兼容旧代码的全局常量（默认取中等长度）
INTRO_MIN_WORDS = LENGTH_CONFIG[IntroLength.medium]["min"]
INTRO_MAX_WORDS = LENGTH_CONFIG[IntroLength.medium]["max"]

# 随机写作角度，确保每次生成内容不同
_STYLE_HINTS = [
    "从用户使用体验出发，以第一人称感受切入",
    "从产品解决痛点的角度切入，突出前后对比",
    "以场景化描述为主，带入具体使用场景",
    "以问句开头引发读者共鸣，再给出解决方案",
    "以产品核心技术为亮点，强调专业性与可靠性",
    "以简洁有力的短句为主，突出产品核心价值",
    "以情感化语言为主，强调生活品质的提升",
    "以对比竞品优势为切入点，突出差异化卖点",
]


class PromptBuilder:
    """LLM提示词构建器"""

    def build_intro_prompt(
        self,
        key_features: list,
        product_info: dict,
        market_info: dict,
        intro_length: IntroLength = IntroLength.medium,
    ) -> str:
        """
        构建产品简介生成提示词
        :param key_features: 核心卖点
        :param product_info: 产品信息字典
        :param market_info: 市场信息字典
        :param intro_length: 简介长度枚举（short/medium/long）
        :return: 完整提示词
        """
        # 使用原始产品名称，去掉地区后缀
        title = product_info.get("original_title", product_info["title"])
        # 如果没有original_title，尝试从title中去掉地区后缀
        if "_" in title:
            title = title.split("_")[0]
        country = market_info["country"]
        language = market_info["target_language"]
        audience = market_info.get("audience") or "通用人群"

        cfg = LENGTH_CONFIG.get(intro_length, LENGTH_CONFIG[IntroLength.medium])
        word_min = cfg["min"]
        word_max = cfg["max"]
        length_label = cfg["label"]

        features_text = "\n".join([f"- {f}" for f in key_features[:12]]) if key_features else "- 暂无卖点"
        style_hint = random.choice(_STYLE_HINTS)

        prompt = f"""
请以{language}撰写一篇适合{country}市场的跨境电商产品简介，目标人群是{audience}。
产品名称：{title}
核心卖点：
{features_text}

要求：
1. 简介为【{length_label}文版】，长度控制在 {word_min}-{word_max} 词（或汉字）之间
2. 突出核心卖点，语言生动有吸引力
3. 符合{country}市场的消费习惯
4. 本次写作角度：{style_hint}
5. 确保本次生成内容在结构、开头、表达方式上与之前版本有明显差异
6. 仅返回简介文本，无其他多余内容
"""
        return prompt.strip()
