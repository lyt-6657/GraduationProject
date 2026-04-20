import os
import logging
import hashlib
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, "server.env")
load_dotenv(dotenv_path=ENV_PATH)

# 优先使用完整的 MONGODB_URI
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "graduation_project")

# 加密密钥
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "66a42432-8f31-4212-9ac7-f891561ad636")


_client: AsyncIOMotorClient = None


def _get_key():
    """
    获取加密密钥
    
    Returns:
        bytes: 加密密钥
    """
    return hashlib.sha256(ENCRYPTION_KEY.encode()).digest()


def encrypt_data(data: str) -> str:
    """
    加密数据
    
    Args:
        data: 要加密的数据
        
    Returns:
        str: 加密后的数据
    """
    try:
        key = _get_key()
        encrypted = bytearray()
        for i, c in enumerate(data.encode()):
            encrypted.append(c ^ key[i % len(key)])
        return encrypted.hex()
    except Exception as e:
        logger.error(f"加密数据失败: {e}")
        return data


def decrypt_data(data: str) -> str:
    """
    解密数据
    
    Args:
        data: 要解密的数据
        
    Returns:
        str: 解密后的数据
    """
    try:
        key = _get_key()
        encrypted = bytearray.fromhex(data)
        decrypted = bytearray()
        for i, c in enumerate(encrypted):
            decrypted.append(c ^ key[i % len(key)])
        return decrypted.decode()
    except Exception as e:
        logger.error(f"解密数据失败: {e}")
        return data


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        # 检查是否启用 TLS/SSL
        use_tls = os.getenv("MONGODB_USE_TLS", "false").lower() == "true"
        
        # 构建连接参数
        client_kwargs = {
            "maxPoolSize": 100,  # 最大连接数
            "minPoolSize": 10,   # 最小连接数
            "serverSelectionTimeoutMS": 5000,  # 服务器选择超时
            "socketTimeoutMS": 20000,  # 套接字超时
            "connectTimeoutMS": 10000,  # 连接超时
        }
        
        # 如果启用 TLS/SSL
        if use_tls:
            client_kwargs["tls"] = True
            # 检查 MONGODB_URI 是否包含 tls 参数
            if "tls=" not in MONGODB_URI:
                # 如果不包含，添加 tls=true 参数
                if "?" in MONGODB_URI:
                    uri_with_tls = MONGODB_URI + "&tls=true"
                else:
                    uri_with_tls = MONGODB_URI + "?tls=true"
                _client = AsyncIOMotorClient(uri_with_tls, **client_kwargs)
            else:
                _client = AsyncIOMotorClient(MONGODB_URI, **client_kwargs)
        else:
            # 不启用 TLS/SSL
            _client = AsyncIOMotorClient(MONGODB_URI, **client_kwargs)
    return _client


def get_db():
    return get_client()


def get_market_knowledge_collection():
    """市场本地化知识库集合"""
    return get_client()[MONGODB_DB_NAME]["market_knowledge"]


def get_consumer_preferences_collection():
    """消费者偏好数据集合"""
    return get_client()[MONGODB_DB_NAME]["consumer_preferences"]


def get_product_records_collection():
    """商品参数记录集合"""
    return get_client()[MONGODB_DB_NAME]["product_records"]


def get_product_intros_collection():
    """商品简介生成记录集合"""
    return get_client()[MONGODB_DB_NAME]["product_intros"]


async def close_connection():
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB连接已关闭")
