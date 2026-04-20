import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.configs: Dict[str, Any] = {}
        self.load_env()
        self.load_config_files()
    
    def load_env(self):
        """加载环境变量"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_path = os.path.join(base_dir, "server.env")
        load_dotenv(dotenv_path=env_path)
    
    def load_config_files(self):
        """加载配置文件"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_dir = os.path.join(base_dir, "config")
        
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # 加载语言配置
        lang_config_path = os.path.join(config_dir, "languages.json")
        if os.path.exists(lang_config_path):
            with open(lang_config_path, "r", encoding="utf-8") as f:
                self.configs["languages"] = json.load(f)
        else:
            # 默认语言配置
            self.configs["languages"] = {
                "supported_languages": ["zh", "en", "ru", "ja", "ko", "ar"],
                "language_names": {
                    "zh": "中文",
                    "en": "English",
                    "ru": "Русский",
                    "ja": "日本語",
                    "ko": "한국어",
                    "ar": "العربية"
                }
            }
            # 保存默认配置
            with open(lang_config_path, "w", encoding="utf-8") as f:
                json.dump(self.configs["languages"], f, ensure_ascii=False, indent=2)
        
        # 加载平台规则配置
        platform_config_path = os.path.join(config_dir, "platforms.json")
        if os.path.exists(platform_config_path):
            with open(platform_config_path, "r", encoding="utf-8") as f:
                self.configs["platforms"] = json.load(f)
        else:
            # 默认平台规则配置
            self.configs["platforms"] = {
                "amazon": {
                    "max_title_length": 200,
                    "max_description_length": 2000,
                    "allowed_html": False
                },
                "ebay": {
                    "max_title_length": 80,
                    "max_description_length": 5000,
                    "allowed_html": True
                },
                "aliexpress": {
                    "max_title_length": 128,
                    "max_description_length": 10000,
                    "allowed_html": True
                }
            }
            # 保存默认配置
            with open(platform_config_path, "w", encoding="utf-8") as f:
                json.dump(self.configs["platforms"], f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，可以使用点号分隔的路径
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        keys = key.split(".")
        value = self.configs
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键，可以使用点号分隔的路径
            value: 配置值
        """
        keys = key.split(".")
        config = self.configs
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self, config_name: str) -> bool:
        """
        保存配置到文件
        
        Args:
            config_name: 配置名称
            
        Returns:
            bool: 是否保存成功
        """
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_dir = os.path.join(base_dir, "config")
            config_path = os.path.join(config_dir, f"{config_name}.json")
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.configs.get(config_name, {}), f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False


# 全局配置管理器实例
config = ConfigManager()
