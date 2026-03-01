from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerateIntroRequest, GenerateIntroResponse
from app.core.feature_extractor import FeatureExtractor
from app.core.prompt_builder import PromptBuilder
from app.core.llm_client import LLMClient

# 初始化路由
router = APIRouter(prefix="/api/v1", tags=["产品简介生成"])

# 核心类实例化
feature_extractor = FeatureExtractor()
prompt_builder = PromptBuilder()
llm_client = LLMClient()

@router.post("/generate-intro", response_model=GenerateIntroResponse)
async def generate_intro(request: GenerateIntroRequest):
    """
    完整参数生成产品简介
    - 接收产品信息+市场信息，返回卖点和简介
    """
    try:
        # 1. 提取核心卖点
        key_features = feature_extractor.extract_key_features(request.product_info)
        
        # 2. 构建LLM提示词
        prompt = prompt_builder.build_intro_prompt(
            key_features=key_features,
            product_info=request.product_info.dict(),
            market_info=request.market_info.dict()
        )
        
        # 3. 调用LLM生成简介
        product_intro = llm_client.generate_text(prompt)
        
        # 4. 构建响应
        if product_intro:
            return GenerateIntroResponse(
                success=True,
                key_features=key_features,
                product_intro=product_intro.strip()
            )
        else:
            return GenerateIntroResponse(
                success=False,
                error="LLM未返回有效简介内容"
            )

        key_features = feature_extractor.extract_key_features(request.product_info)
        print(f"提取的卖点：{key_features}")  
    
    except ValueError as e:
        # 业务逻辑错误
        return GenerateIntroResponse(
            success=False,
            error=f"参数错误：{str(e)}"
        )
    except Exception as e:
        # 未知异常
        raise HTTPException(status_code=500, detail=f"服务器内部错误：{str(e)}")