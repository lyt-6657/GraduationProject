"""初始化MongoDB市场本地化知识库数据"""
import asyncio
import logging
from app.core.database import get_market_knowledge_collection

logger = logging.getLogger(__name__)

# 初始市场知识库数据
INITIAL_MARKET_DATA = [
    {
        "country_code": "USA",
        "country_name": "美国",
        "region": "北美",
        "target_language": "English",
        "preferences": "喜欢简洁、直接的描述，强调品质、便捷性、性价比",
        "taboos": "避免使用歧视性语言，禁用虚假宣传词汇如'best'、'perfect'",
        "language_style": "口语化、简洁有力"
    },
    {
        "country_code": "JAPAN",
        "country_name": "日本",
        "region": "东亚",
        "target_language": "Japanese",
        "preferences": "注重细节、品质、环保，喜欢礼貌、正式的表达",
        "taboos": "避免使用数字4，禁用夸张宣传",
        "language_style": "正式、礼貌、注重细节描述"
    },
    {
        "country_code": "GERMANY",
        "country_name": "德国",
        "region": "欧洲",
        "target_language": "German",
        "preferences": "注重精准、专业、高品质，喜欢详细的技术参数",
        "taboos": "禁用模糊表述，如'大概'、'可能'",
        "language_style": "专业、严谨、数据化"
    },
    {
        "country_code": "UK",
        "country_name": "英国",
        "region": "欧洲",
        "target_language": "English",
        "preferences": "注重品质与传统，欣赏幽默和含蓄表达，重视品牌故事",
        "taboos": "避免过度夸张和美式直白风格",
        "language_style": "正式中带有英式幽默，措辞考究"
    },
    {
        "country_code": "FRANCE",
        "country_name": "法国",
        "region": "欧洲",
        "target_language": "French",
        "preferences": "重视美感、时尚、艺术性，偏好优雅表达",
        "taboos": "避免过于功能性描述，忽视美学价值",
        "language_style": "优雅、艺术化、情感化"
    },
    {
        "country_code": "BRAZIL",
        "country_name": "巴西",
        "region": "南美",
        "target_language": "Portuguese",
        "preferences": "热情奔放，注重社交属性，喜欢鲜艳色彩相关描述",
        "taboos": "避免过于保守和正式的表达",
        "language_style": "热情、活泼、强调社交价值"
    },
    {
        "country_code": "INDIA",
        "country_name": "印度",
        "region": "南亚",
        "target_language": "English",
        "preferences": "注重性价比、家庭价值、耐用性，宗教文化多元",
        "taboos": "避免牛相关内容，注意宗教文化敏感性",
        "language_style": "强调价值感、家庭属性、实用性"
    },
    {
        "country_code": "SOUTH_KOREA",
        "country_name": "韩国",
        "region": "东亚",
        "target_language": "Korean",
        "preferences": "注重外观设计、潮流感、科技感，K-pop文化影响大",
        "taboos": "避免日本风格联想，注意历史敏感话题",
        "language_style": "时尚、科技感强、强调外观与颜值"
    },
    {
        "country_code": "AUSTRALIA",
        "country_name": "澳大利亚",
        "region": "大洋洲",
        "target_language": "English",
        "preferences": "户外运动、环保、轻松随意的生活方式",
        "taboos": "避免过于正式和严肃的表达",
        "language_style": "轻松、友好、强调户外与生活方式"
    },
    {
        "country_code": "CANADA",
        "country_name": "加拿大",
        "region": "北美",
        "target_language": "English",
        "preferences": "注重多元文化包容性、环保意识强、品质优先",
        "taboos": "避免单一文化视角，注意双语（英法）需求",
        "language_style": "包容、温和、注重可持续性"
    },
    {
        "country_code": "MEXICO",
        "country_name": "墨西哥",
        "region": "拉丁美洲",
        "target_language": "Spanish",
        "preferences": "重视家庭、节日文化、鲜艳色彩，价格敏感",
        "taboos": "避免忽视家庭价值观的表达",
        "language_style": "热情、家庭导向、节日氛围感"
    },
    {
        "country_code": "SAUDI_ARABIA",
        "country_name": "沙特阿拉伯",
        "region": "中东",
        "target_language": "Arabic",
        "preferences": "注重奢华、品质、宗教合规，男性消费力强",
        "taboos": "严格避免违反伊斯兰教义内容，不得有女性暴露图像描述",
        "language_style": "尊重、正式、强调奢华与品质"
    }
]


async def init_market_knowledge():
    """初始化市场知识库到MongoDB（已存在则跳过）"""
    collection = get_market_knowledge_collection()
    try:
        count = await collection.count_documents({})
        if count == 0:
            await collection.insert_many(INITIAL_MARKET_DATA)
            logger.info(f"已初始化 {len(INITIAL_MARKET_DATA)} 条市场知识库数据")
        else:
            logger.info(f"市场知识库已存在 {count} 条数据，跳过初始化")
        # 创建索引
        await collection.create_index("country_code", unique=True)
    except Exception as e:
        logger.error(f"初始化市场知识库失败: {e}")


if __name__ == "__main__":
    asyncio.run(init_market_knowledge())
