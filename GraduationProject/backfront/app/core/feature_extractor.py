import logging
from typing import List
from app.models.schemas import ProductInfo

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeatureExtractor:
    """产品卖点提取器"""
    def extract_key_features(self, product_info: ProductInfo) -> List[str]:
        """
        基于规则提取产品核心卖点
        :param product_info: 产品信息对象
        :return: 卖点列表
        """
        key_features = []
        try:
            # 从描述中提取核心卖点
            desc = product_info.description.lower()
            params = product_info.parameters
            
            # 蓝牙相关
            if "蓝牙" in desc:
                version = params.get("蓝牙版本", "5.3")
                key_features.append(f"蓝牙{version}技术，连接稳定无延迟")
            
            # 续航相关
            if "续航" in desc:
                duration = params.get("续航", "30小时")
                key_features.append(f"超长续航，{duration}持续使用")
            
            # 防水相关
            if "防水" in desc:
                level = params.get("防水等级", "IPX7")
                key_features.append(f"{level}级防水，适应多种场景")
            
            # 降噪相关
            if "降噪" in desc:
                key_features.append("主动降噪技术，沉浸式音效体验")
            
            # 竞品对比优势
            for comp_feature in product_info.competitor_features:
                if "续航" in comp_feature and "续航" in desc:
                    key_features.append(f"续航远超竞品（竞品仅{comp_feature}）")
            
            logger.info(f"成功提取卖点，数量：{len(key_features)}")
            return key_features
        
        except Exception as e:
            logger.error(f"提取卖点失败：{str(e)}")
            return key_features  # 异常返回空列表