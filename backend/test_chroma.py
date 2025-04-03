import os
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入chromadb
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    logger.error("chromadb package is not installed. Please install it with 'pip install chromadb'")
    sys.exit(1)

# 获取Chroma数据库路径
base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
chroma_path = os.path.join(base_path, "03-vector-store/langchain_chroma.db")
logger.info(f"Using Chroma path: {chroma_path}")

# 确保目录存在
if not os.path.exists(chroma_path):
    logger.warning(f"Chroma directory does not exist: {chroma_path}")
    sys.exit(1)

# 创建客户端
try:
    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # 获取所有集合
    collections = client.list_collections()
    logger.info(f"Successfully retrieved {len(collections)} collections from Chroma")
    
    # 打印集合信息
    for i, collection in enumerate(collections):
        logger.info(f"Collection {i+1}:")
        logger.info(f"  Name: {collection.name}")
        logger.info(f"  Metadata: {collection.metadata}")
        
        # 获取集合中的文档数量
        count = collection.count()
        logger.info(f"  Document count: {count}")
        
except Exception as e:
    logger.error(f"Error querying Chroma: {str(e)}", exc_info=True)
    sys.exit(1) 