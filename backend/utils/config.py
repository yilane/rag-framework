import os
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class VectorDBProvider(Enum):
    MILVUS = "milvus"
    CHROMA = "chroma"
    # More providers can be added later
    
    @classmethod
    def from_string(cls, provider_str: str):
        """
        从字符串创建枚举值，不区分大小写
        
        Args:
            provider_str: 提供商字符串
            
        Returns:
            VectorDBProvider枚举值
        """
        if not provider_str:
            return cls.MILVUS
            
        # 确保输入是字符串
        if not isinstance(provider_str, str):
            provider_str = str(provider_str)
            
        provider_str = provider_str.lower().strip()
        
        # 创建值到枚举的映射
        value_map = {
            "milvus": cls.MILVUS,
            "chroma": cls.CHROMA
        }
        
        # 检查完全匹配
        if provider_str in value_map:
            return value_map[provider_str]
            
        # 检查部分匹配
        for key, enum_val in value_map.items():
            if key in provider_str or provider_str in key:
                return enum_val
                
        # 默认返回MILVUS
        return cls.MILVUS

# 可以在这里添加其他配置相关的内容

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

    # Server Settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8001"))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    # Logging Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

# 创建全局配置实例
config = Config()

MILVUS_CONFIG = {
    "uri": "03-vector-store/langchain_milvus.db",
    "index_types": {
        "flat": "FLAT",
        "hnsw": "HNSW",
        "autoindex": "AUTOINDEX",
        # Milvus Lite不支持的索引类型（保留用于服务器模式）
        "ivf_flat": "FLAT",    # 降级到FLAT
        "ivf_sq8": "HNSW"      # 降级到HNSW
    },
    "index_params": {
        "flat": {},
        "hnsw": {
            "M": 16,
            "efConstruction": 200
        },
        "autoindex": {},
        # 降级后的参数
        "ivf_flat": {},        # FLAT不需要参数
        "ivf_sq8": {           # HNSW参数
            "M": 16,
            "efConstruction": 200
        }
    }
} 


# Chroma向量数据库配置
CHROMA_CONFIG = {
    "uri": "03-vector-store/langchain_chroma.db",
    "index_types": {
        "hnsw": "HNSW",
        "standard": "STANDARD"
    },
    "index_params": {
        "hnsw": {
            "M": 16,            # 每个节点的最大连接数
            "efConstruction": 100,  # 构建时的搜索深度
            "efSearch": 50      # 搜索时的搜索深度
        },
        "standard": {}         # 标准索引不需要额外参数
    }
}