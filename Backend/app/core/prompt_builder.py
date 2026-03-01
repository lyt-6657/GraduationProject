class PromptBuilder:
    """LLM提示词构建器"""
    def build_intro_prompt(self, key_features: list, product_info: dict, market_info: dict) -> str:
        """
        构建产品简介生成提示词
        :param key_features: 核心卖点
        :param product_info: 产品信息字典
        :param market_info: 市场信息字典
        :return: 完整提示词
        """
        # 基础信息拼接
        title = product_info["title"]
        country = market_info["country"]
        language = market_info["target_language"]
        audience = market_info["audience"] or "通用人群"
        
        # 卖点拼接
        features_text = "\n".join([f"- {f}" for f in key_features])
        
        # 提示词模板
        prompt = f"""
        请以{language}撰写一篇适合{country}市场的跨境电商产品简介，目标人群是{audience}。
        产品名称：{title}
        核心卖点：
        {features_text}
        
        要求：
        1. 简介长度100-150词
        2. 突出核心卖点，语言生动有吸引力
        3. 符合{country}市场的消费习惯
        4. 仅返回简介文本，无其他多余内容
        """
        return prompt.strip()