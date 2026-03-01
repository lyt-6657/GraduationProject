# 预设的市场本地化知识库（可扩展为数据库存储）
MARKET_KNOWLEDGE = {
    "USA": {
        "preferences": "喜欢简洁、直接的描述，强调品质、便捷性、性价比",
        "taboos": "避免使用歧视性语言，禁用虚假宣传词汇如'best'、'perfect'",
        "language_style": "口语化、简洁有力"
    },
    "Japan": {
        "preferences": "注重细节、品质、环保，喜欢礼貌、正式的表达",
        "taboos": "避免使用数字4，禁用夸张宣传",
        "language_style": "正式、礼貌、注重细节描述"
    },
    "Germany": {
        "preferences": "注重精准、专业、高品质，喜欢详细的技术参数",
        "taboos": "禁用模糊表述，如'大概'、'可能'",
        "language_style": "专业、严谨、数据化"
    }
}

class LocalizationAdapter:
    def __init__(self):
        self.market_knowledge = MARKET_KNOWLEDGE

    def get_localization_rules(self, country: str) -> dict:
        """
        获取目标市场的本地化规则
        :param country: 国家/地区代码
        :return: 本地化规则字典
        """
        return self.market_knowledge.get(country.upper(), {
            "preferences": "通用偏好，注重产品核心价值",
            "taboos": "无特殊禁忌",
            "language_style": "通用商业风格"
        })

    def adapt_prompt(self, prompt: str, country: str, target_language: str) -> str:
        """
        根据本地化规则适配提示词
        :param prompt: 原始提示词
        :param country: 目标国家
        :param target_language: 目标语言
        :return: 适配后的提示词
        """
        rules = self.get_localization_rules(country)
        localization_prompt = f"""
        额外要求：
        1. 语言必须为{target_language}，符合{country}的语言表达习惯
        2. 遵循{country}的消费偏好：{rules['preferences']}
        3. 严格避免{country}的文化禁忌：{rules['taboos']}
        4. 整体风格保持：{rules['language_style']}
        """
        return prompt + localization_prompt