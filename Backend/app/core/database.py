import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, "server.env")
load_dotenv(dotenv_path=ENV_PATH)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "graduation_project")

_client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client


def get_db():
    return get_client()[MONGODB_DB_NAME]


def get_market_knowledge_collection():
    """市场本地化知识库集合"""
    return get_db()["market_knowledge"]


def get_consumer_preferences_collection():
    """消费者偏好数据集合"""
    return get_db()["consumer_preferences"]


async def close_connection():
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("MongoDB连接已关闭")
