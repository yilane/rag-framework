from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from pymilvus import connections, Collection, utility
from services.vector_store_service import VectorStoreService
from services.embedding_service import EmbeddingService, EmbeddingProvider
from utils.config import VectorDBProvider, MILVUS_CONFIG, CHROMA_CONFIG
import os
import json
import re

logger = logging.getLogger(__name__)

class SearchService:
    """
    搜索服务类，负责向量数据库的连接和向量搜索功能
    提供集合列表查询、向量相似度搜索和搜索结果保存等功能
    """
    def __init__(self, provider: str = VectorDBProvider.MILVUS.value):
        """
        初始化搜索服务
        创建嵌入服务实例，设置数据库连接URI，初始化搜索结果保存目录
        
        Args:
            provider (str): 向量数据库提供商，默认为Milvus
        """
        self.embedding_service = EmbeddingService()
        self.current_provider = provider
        self.search_results_dir = "04-search-results"
        os.makedirs(self.search_results_dir, exist_ok=True)

    def get_uri(self, provider: str = None) -> str:
        """
        根据提供商获取对应的数据库URI
        
        Args:
            provider (str): 向量数据库提供商，如果为None则使用当前提供商
            
        Returns:
            str: 数据库URI
        """
        provider = provider or self.current_provider
        if provider == VectorDBProvider.MILVUS.value:
            return MILVUS_CONFIG["uri"]
        elif provider == VectorDBProvider.CHROMA.value:
            return CHROMA_CONFIG["uri"]
        else:
            raise ValueError(f"Unsupported vector database provider: {provider}")

    def set_provider(self, provider: str):
        """
        设置当前使用的向量数据库提供商
        
        Args:
            provider (str): 向量数据库提供商
        """
        self.current_provider = provider

    def get_providers(self) -> List[Dict[str, str]]:
        """
        获取支持的向量数据库列表
        
        Returns:
            List[Dict[str, str]]: 支持的向量数据库提供商列表
        """
        return [
            {"id": VectorDBProvider.MILVUS.value, "name": "Milvus"},
            {"id": VectorDBProvider.CHROMA.value, "name": "Chroma"},
        ]

    def list_collections(self, provider: str = VectorDBProvider.MILVUS.value) -> List[Dict[str, Any]]:
        """
        获取指定向量数据库中的所有集合
        
        Args:
            provider (str): 向量数据库提供商，默认为Milvus
            
        Returns:
            List[Dict[str, Any]]: 集合信息列表，包含id、名称和实体数量
            
        Raises:
            Exception: 连接或查询集合时发生错误
        """
        logger.info(f"Listing collections for provider: {provider}")
        
        if provider == VectorDBProvider.MILVUS.value:
            try:
                connections.connect(
                    alias="default",
                    uri=self.get_uri(provider)
                )
                
                collections = []
                collection_names = utility.list_collections()
                
                for name in collection_names:
                    try:
                        collection = Collection(name)
                        collections.append({
                            "id": name,
                            "name": name,
                            "count": collection.num_entities
                        })
                    except Exception as e:
                        logger.error(f"Error getting info for collection {name}: {str(e)}")
                
                return collections
                
            except Exception as e:
                logger.error(f"Error listing Milvus collections: {str(e)}")
                raise
            finally:
                connections.disconnect("default")
        
        elif provider == VectorDBProvider.CHROMA.value:
            try:
                # 导入chromadb
                import chromadb
                from chromadb.config import Settings
                
                # 获取Chroma路径
                vector_store = VectorStoreService()
                chroma_path = vector_store._get_absolute_path(CHROMA_CONFIG["uri"])
                logger.info(f"Listing collections from Chroma path: {chroma_path}")
                
                # 确保目录存在
                if not os.path.exists(chroma_path):
                    logger.warning(f"Chroma directory does not exist: {chroma_path}, creating it")
                
                # 创建客户端
                client = chromadb.PersistentClient(
                    path=chroma_path,
                    settings=Settings(anonymized_telemetry=False)
                )
                
                # 获取所有集合
                collections = client.list_collections()
                logger.info(f"Successfully retrieved {len(collections)} collections from Chroma")
                logger.info(f"Raw Chroma collections: {collections}")
                
                # 转换为统一的返回格式
                result = []
                for col in collections:
                    try:
                        count = col.count()
                        result.append({
                            "id": col.name,
                            "name": col.name,
                            "count": count
                        })
                    except Exception as e:
                        logger.error(f"Error getting count for collection {col.name}: {str(e)}")
                        result.append({
                            "id": col.name,
                            "name": col.name,
                            "count": 0
                        })
                
                logger.info(f"Formatted Chroma collections: {result}")
                return result
                
            except ImportError as e:
                logger.error(f"ChromaDB package is not installed: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"Error listing Chroma collections: {str(e)}")
                return []
        
        else:
            logger.error(f"Unsupported vector database provider: {provider}")
            raise ValueError(f"Unsupported vector database provider: {provider}")

    def save_search_results(self, query: str, collection_id: str, results: List[Dict[str, Any]]) -> str:
        """
        保存搜索结果到JSON文件
        
        Args:
            query (str): 搜索查询文本
            collection_id (str): 集合ID
            results (List[Dict[str, Any]]): 搜索结果列表
            
        Returns:
            str: 保存文件的路径
            
        Raises:
            Exception: 保存文件时发生错误
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            # 使用集合ID的基础名称（去掉路径相关字符）
            collection_base = os.path.basename(collection_id)
            filename = f"search_{collection_base}_{timestamp}.json"
            filepath = os.path.join(self.search_results_dir, filename)
            
            search_data = {
                "query": query,
                "collection_id": collection_id,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }
            
            logger.info(f"Saving search results to: {filepath}")
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(search_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully saved search results to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving search results: {str(e)}")
            raise

    async def search(self, 
                   provider: str,
                   query: str, 
                   collection_id: str, 
                   top_k: int = 3, 
                   threshold: float = 0.5,    # 相似度阈值默认50%
                   word_count_threshold: int = 30,    # 最小字数默认30
                   save_results: bool = False) -> Dict[str, Any]:
        """
        执行向量搜索
        
        Args:
            provider (str): 向量数据库提供商
            query (str): 搜索查询文本
            collection_id (str): 要搜索的集合ID
            top_k (int): 返回的最大结果数量，默认为3
            threshold (float): 相似度阈值，低于此值的结果将被过滤，默认为0.7
            word_count_threshold (int): 文本字数阈值，低于此值的结果将被过滤，默认为20
            save_results (bool): 是否保存搜索结果，默认为False
            
        Returns:
            Dict[str, Any]: 包含搜索结果的字典，如果保存结果则包含保存路径
            
        Raises:
            Exception: 搜索过程中发生错误
        """
        try:
            # 添加参数日志
            logger.info(f"Search parameters:")
            logger.info(f"- Provider: {provider} (type: {type(provider)})")
            logger.info(f"- Query: {query}")
            logger.info(f"- Collection ID: {collection_id}")
            logger.info(f"- Top K: {top_k}")
            logger.info(f"- Threshold: {threshold}")
            logger.info(f"- Word Count Threshold: {word_count_threshold}")
            logger.info(f"- Save Results: {save_results} (type: {type(save_results)})")

            logger.info(f"Starting search with parameters - Provider: {provider}, Collection: {collection_id}, Query: {query}, Top K: {top_k}")
            
            # 确保 provider 参数是字符串，并规范化为小写进行比较
            provider_str = str(provider).lower().strip()
            
            logger.info(f"Normalized provider: {provider_str}")
            logger.info(f"MILVUS value: {VectorDBProvider.MILVUS.value} (lowercased: {VectorDBProvider.MILVUS.value.lower()})")
            logger.info(f"CHROMA value: {VectorDBProvider.CHROMA.value} (lowercased: {VectorDBProvider.CHROMA.value.lower()})")
            
            # 严格检查提供商字符串
            is_milvus = provider_str == VectorDBProvider.MILVUS.value.lower()
            is_chroma = provider_str == VectorDBProvider.CHROMA.value.lower()
            
            logger.info(f"Is MILVUS? {is_milvus}")
            logger.info(f"Is CHROMA? {is_chroma}")
            
            if is_milvus:
                # Milvus搜索逻辑
                logger.info("Using Milvus search logic")
                return await self._search_milvus(
                    query=query,
                    collection_id=collection_id,
                    top_k=top_k,
                    threshold=threshold,
                    word_count_threshold=word_count_threshold,
                    save_results=save_results
                )
            elif is_chroma:
                # Chroma搜索逻辑
                logger.info("Using Chroma search logic")
                return await self._search_chroma(
                    query=query,
                    collection_id=collection_id,
                    top_k=top_k,
                    threshold=threshold,
                    word_count_threshold=word_count_threshold,
                    save_results=save_results
                )
            else:
                # 如果前面的比较都不匹配，则提供明确的错误信息
                logger.error(f"Unsupported vector database provider: '{provider_str}'")
                logger.error(f"Supported providers are: {VectorDBProvider.MILVUS.value}, {VectorDBProvider.CHROMA.value}")
                return {
                    "results": [],
                    "error": f"Unsupported vector database provider: '{provider_str}'"
                }
                
        except Exception as e:
            logger.error(f"Error in search method: {str(e)}", exc_info=True)
            return {
                "results": [],
                "error": f"Search failed: {str(e)}"
            }
            
    async def _search_milvus(self, 
                          query: str, 
                          collection_id: str, 
                          top_k: int = 3, 
                          threshold: float = 0.5,    # 相似度阈值默认50%
                          word_count_threshold: int = 30,    # 最小字数默认30
                          save_results: bool = False) -> Dict[str, Any]:
        """
        在Milvus中执行向量搜索
        
        Args:
            query (str): 搜索查询文本
            collection_id (str): 要搜索的集合ID
            top_k (int): 返回的最大结果数量，默认为3
            threshold (float): 相似度阈值，低于此值的结果将被过滤，默认为0.7
            word_count_threshold (int): 文本字数阈值，低于此值的结果将被过滤，默认为20
            save_results (bool): 是否保存搜索结果，默认为False
            
        Returns:
            Dict[str, Any]: 包含搜索结果的字典，如果保存结果则包含保存路径
        """
        try:
            # 连接到向量数据库
            logger.info(f"Connecting to Milvus at {self.get_uri(VectorDBProvider.MILVUS.value)}")
            connections.connect(
                alias="default",
                uri=self.get_uri(VectorDBProvider.MILVUS.value)
            )
            
            # 获取collection
            logger.info(f"Loading collection: {collection_id}")
            collection = Collection(collection_id)
            collection.load()
            
            # 记录collection的基本信息
            logger.info(f"Collection info - Entities: {collection.num_entities}")
            
            # 从collection中读取embedding配置
            logger.info("Querying sample entity for embedding configuration")
            sample_entity = collection.query(
                expr="id >= 0", 
                output_fields=["embedding_provider", "embedding_model"],
                limit=1
            )
            if not sample_entity:
                logger.error(f"Collection {collection_id} is empty")
                raise ValueError(f"Collection {collection_id} is empty")
            
            logger.info(f"Sample entity configuration: {sample_entity[0]}")
            
            # 使用collection中存储的配置创建查询向量
            logger.info("Creating query embedding")
            try:
                query_embedding = self.embedding_service.create_single_embedding(
                    query,
                    provider=sample_entity[0]["embedding_provider"],
                    model=sample_entity[0]["embedding_model"]
                )
                logger.info(f"Query embedding created with dimension: {len(query_embedding)}")
            except Exception as e:
                logger.error(f"Error creating embedding: {str(e)}")
                # 尝试使用备用模型
                try:
                    logger.info("Trying with a backup model...")
                    query_embedding = self.embedding_service.create_single_embedding(
                        query,
                        provider=EmbeddingProvider.HUGGINGFACE.value,
                        model="paraphrase-multilingual-MiniLM-L12-v2"  # 使用更可靠的备用模型
                    )
                    logger.info(f"Backup embedding created with dimension: {len(query_embedding)}")
                except Exception as backup_error:
                    logger.error(f"Backup embedding also failed: {str(backup_error)}")
                    return {
                        "results": [],
                        "error": f"Failed to create embedding: {str(e)}. Backup also failed: {str(backup_error)}"
                    }
            
            # 执行搜索
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            logger.info(f"Executing search with params: {search_params}")
            logger.info(f"Word count threshold filter: word_count >= {word_count_threshold}")
            
            results = collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=f"word_count >= {word_count_threshold}",
                output_fields=[
                    "content",
                    "document_name",
                    "chunk_id",
                    "total_chunks",
                    "word_count",
                    "page_number",
                    "page_range",
                    "embedding_provider",
                    "embedding_model",
                    "embedding_timestamp"
                ]
            )
            
            # 处理结果
            processed_results = []
            logger.info(f"Raw search results count: {len(results[0])}")
            
            for hits in results:
                for hit in hits:
                    logger.info(f"Processing hit - Score: {hit.score}, Word Count: {hit.entity.get('word_count')}")
                    if hit.score >= threshold:
                        processed_results.append({
                            "text": hit.entity.content,
                            "score": float(hit.score),
                            "metadata": {
                                "source": hit.entity.document_name,
                                "page": hit.entity.page_number,
                                "chunk": hit.entity.chunk_id,
                                "total_chunks": hit.entity.total_chunks,
                                "page_range": hit.entity.page_range,
                                "embedding_provider": hit.entity.embedding_provider,
                                "embedding_model": hit.entity.embedding_model,
                                "embedding_timestamp": hit.entity.embedding_timestamp
                            }
                        })

            response_data = {"results": processed_results}
            
            # 添加详细的保存逻辑日志
            logger.info(f"Preparing to handle save_results (flag: {save_results})")
            if save_results:
                logger.info("Save results is True, attempting to save...")
                if processed_results:
                    try:
                        filepath = self.save_search_results(query, collection_id, processed_results)
                        logger.info(f"Successfully saved results to: {filepath}")
                        response_data["saved_filepath"] = filepath
                    except Exception as e:
                        logger.error(f"Error saving search results: {str(e)}")
                else:
                    logger.info("No results to save, skipping save operation")
            
            return response_data
        
        except Exception as e:
            logger.error(f"Error in _search_milvus: {str(e)}", exc_info=True)
            return {
                "results": [],
                "error": f"Search failed: {str(e)}"
            }
        finally:
            try:
                connections.disconnect("default")
                logger.info("Disconnected from Milvus")
            except Exception as e:
                logger.error(f"Error disconnecting from Milvus: {str(e)}")
                
    async def _search_chroma(self, 
                          query: str, 
                          collection_id: str, 
                          top_k: int = 3, 
                          threshold: float = 0.5,    # 相似度阈值默认50%
                          word_count_threshold: int = 30,    # 最小字数默认30
                          save_results: bool = False) -> Dict[str, Any]:
        """
        在Chroma中执行向量搜索
        
        Args:
            query (str): 搜索查询文本
            collection_id (str): 要搜索的集合ID
            top_k (int): 返回的最大结果数量，默认为3
            threshold (float): 相似度阈值，低于此值的结果将被过滤，默认为0.7
            word_count_threshold (int): 文本字数阈值，低于此值的结果将被过滤，默认为20
            save_results (bool): 是否保存搜索结果，默认为False
            
        Returns:
            Dict[str, Any]: 包含搜索结果的字典，如果保存结果则包含保存路径
        """
        try:
            # 导入chromadb
            import chromadb
            from chromadb.config import Settings
            
            # 先检查集合ID是否为有效的Chroma集合名称
            original_collection_id = collection_id
            logger.info(f"Original collection ID: '{original_collection_id}'")
            
            # 获取Chroma路径
            vector_store = VectorStoreService()
            chroma_path = vector_store._get_absolute_path(CHROMA_CONFIG["uri"])
            logger.info(f"Connecting to Chroma at {chroma_path}")
            
            # 创建客户端
            client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 先列出所有集合，检查目标集合是否存在
            all_collections = client.list_collections()
            collection_names = [col.name for col in all_collections]
            
            logger.info(f"Available collections: {collection_names}")
            logger.info(f"Requested collection: '{collection_id}' (type: {type(collection_id)})")
            
            # 详细输出每个集合名的信息
            logger.info("Detailed collection comparison:")
            for i, name in enumerate(collection_names):
                is_same = name == collection_id
                contains = collection_id in name
                logger.info(f"Collection {i+1}: '{name}' vs '{collection_id}' - Is same: {is_same}, Contains: {contains}")
            
            # 尝试找到匹配的集合名称 - 优先精确匹配，然后尝试部分匹配
            if collection_id in collection_names:
                logger.info(f"Found exact match for collection: '{collection_id}'")
            else:
                # 如果没有精确匹配，试着用不同的方式处理集合名称
                
                # 尝试方式1: 替换连字符为下划线后再查找
                if "-" in collection_id:
                    mod_collection_id = collection_id.replace("-", "_")
                    if mod_collection_id in collection_names:
                        logger.info(f"Found match after replacing hyphens: '{mod_collection_id}'")
                        collection_id = mod_collection_id
                
                # 尝试方式2: 如果集合名列表中有一个条目包含原始ID，使用该条目
                elif not collection_id in collection_names:
                    for name in collection_names:
                        if collection_id in name:
                            logger.info(f"Found partial match (original in collection): '{name}'")
                            collection_id = name
                            break
                        elif name in collection_id:
                            logger.info(f"Found partial match (collection in original): '{name}'")
                            collection_id = name
                            break
                            
                # 尝试方式3: 作为最后的手段，直接使用列表中的第一个集合
                if not collection_id in collection_names and collection_names:
                    collection_id = collection_names[0]
                    logger.warning(f"No match found, using first available collection: '{collection_id}'")
            
            # 如果尝试了所有方法仍找不到集合，返回错误
            if not collection_id in collection_names:
                logger.error(f"No suitable collection found matching '{original_collection_id}'")
                return {"results": [], "error": f"Collection not found. Available collections: {collection_names}"}
                
            # 到这里，collection_id 应该是一个有效的集合名称
            logger.info(f"Selected collection for search: '{collection_id}'")
            
            # 获取指定集合
            try:
                logger.info(f"Loading collection: '{collection_id}'")
                collection = client.get_collection(name=collection_id)
            except Exception as e:
                logger.error(f"Error getting collection: {str(e)}")
                return {"results": [], "error": f"Failed to get collection: {str(e)}"}
            
            # 创建查询嵌入
            # 由于Chroma需要嵌入，我们需要获取集合的第一个项目来确定使用的嵌入提供商和模型
            logger.info("Querying sample item for embedding configuration")
            try:
                sample_items = collection.peek(limit=1)
                
                if not sample_items or len(sample_items["metadatas"]) == 0:
                    logger.error(f"Collection {collection_id} is empty")
                    return {"results": [], "error": f"Collection {collection_id} is empty"}
                
                sample_metadata = sample_items["metadatas"][0]
                logger.info(f"Sample metadata: {sample_metadata}")
                
                embedding_provider = sample_metadata.get("embedding_provider", "huggingface")
                embedding_model = sample_metadata.get("embedding_model", "all-MiniLM-L6-v2")
            except Exception as e:
                logger.error(f"Error getting sample items: {str(e)}")
                # 使用默认值
                embedding_provider = "huggingface"
                embedding_model = "all-MiniLM-L6-v2"
                logger.info(f"Using default embedding provider: {embedding_provider}, model: {embedding_model}")
            
            logger.info(f"Creating query embedding with provider: {embedding_provider}, model: {embedding_model}")
            try:
                query_embedding = self.embedding_service.create_single_embedding(
                    query,
                    provider=embedding_provider,
                    model=embedding_model
                )
                logger.info(f"Query embedding created with dimension: {len(query_embedding)}")
            except Exception as e:
                logger.error(f"Error creating embedding: {str(e)}")
                # 尝试使用备用模型
                try:
                    logger.info("Trying with a backup model...")
                    query_embedding = self.embedding_service.create_single_embedding(
                        query,
                        provider=EmbeddingProvider.HUGGINGFACE.value,
                        model="paraphrase-multilingual-MiniLM-L12-v2"  # 使用更可靠的备用模型
                    )
                    logger.info(f"Backup embedding created with dimension: {len(query_embedding)}")
                except Exception as backup_error:
                    logger.error(f"Backup embedding also failed: {str(backup_error)}")
                    return {
                        "results": [],
                        "error": f"Failed to create embedding: {str(e)}. Backup also failed: {str(backup_error)}"
                    }
            
            # 执行搜索
            logger.info(f"Executing search with top_k: {top_k}")
            
            try:
                # 首先获取集合的维度信息（如果可能）
                collection_dimension = None
                try:
                    # 尝试从样本元数据中获取维度信息
                    if sample_metadata and "vector_dimension" in sample_metadata:
                        collection_dimension = sample_metadata.get("vector_dimension")
                        logger.info(f"Found collection dimension from metadata: {collection_dimension}")
                    # 如果无法从元数据获取，使用默认值
                    if not collection_dimension:
                        # 根据模型设置默认维度
                        if "mpnet" in embedding_model.lower():
                            collection_dimension = 768
                        elif "minilm" in embedding_model.lower():
                            collection_dimension = 384
                        else:
                            collection_dimension = 768  # 大多数模型是768维
                        logger.info(f"Using default dimension for model {embedding_model}: {collection_dimension}")
                except Exception as e:
                    logger.warning(f"Error determining collection dimension: {str(e)}")
                    collection_dimension = 768  # 默认使用较大维度
                
                # 检查当前查询向量的维度
                current_dimension = len(query_embedding)
                logger.info(f"Current query embedding dimension: {current_dimension}")
                logger.info(f"Required collection dimension: {collection_dimension}")
                
                # 如果维度不匹配，重新创建查询向量
                if collection_dimension and current_dimension != collection_dimension:
                    logger.warning(f"Dimension mismatch: query={current_dimension}, collection={collection_dimension}")
                    
                    # 选择合适维度的模型
                    new_model = None
                    
                    # 检测是否包含中文字符
                    has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in query)
                    if has_chinese:
                        logger.info("Query contains Chinese characters")
                    
                    # 根据维度和语言选择合适的模型
                    if collection_dimension == 768:
                        if has_chinese:
                            # 使用支持中文的768维模型
                            new_model = "distiluse-base-multilingual-cased-v1" # 或 "distiluse-base-multilingual-cased-v2"
                        else:
                            new_model = "all-mpnet-base-v2"  # 768维
                    elif collection_dimension == 384:
                        if has_chinese:
                            # 使用支持中文的384维模型
                            new_model = "paraphrase-multilingual-MiniLM-L12-v2" 
                        else:
                            new_model = "all-MiniLM-L6-v2"  # 384维
                    else:
                        logger.warning(f"Unknown collection dimension: {collection_dimension}, trying to proceed anyway")
                    
                    if new_model:
                        logger.info(f"Recreating embedding with model: {new_model} (dimension: {collection_dimension})")
                        try:
                            query_embedding = self.embedding_service.create_single_embedding(
                                query,
                                provider=EmbeddingProvider.HUGGINGFACE.value,
                                model=new_model
                            )
                            logger.info(f"New query embedding created with dimension: {len(query_embedding)}")
                            
                            # 再次验证维度
                            if len(query_embedding) != collection_dimension:
                                logger.warning(f"Still dimension mismatch after trying model {new_model}. " +
                                             f"Got {len(query_embedding)}, need {collection_dimension}")
                                
                                # 尝试所有可能的模型，直到找到匹配维度的
                                fallback_models = [
                                    "all-mpnet-base-v2",                 # 768维
                                    "distiluse-base-multilingual-cased", # 512维
                                    "all-MiniLM-L12-v2",                 # 384维
                                    "all-MiniLM-L6-v2",                  # 384维
                                    "paraphrase-multilingual-MiniLM-L12-v2" # 384维
                                ]
                                
                                for fallback_model in fallback_models:
                                    if fallback_model == new_model:
                                        continue  # 跳过已尝试的模型
                                    
                                    logger.info(f"Trying fallback model: {fallback_model}")
                                    try:
                                        fallback_embedding = self.embedding_service.create_single_embedding(
                                            query,
                                            provider=EmbeddingProvider.HUGGINGFACE.value,
                                            model=fallback_model
                                        )
                                        
                                        if len(fallback_embedding) == collection_dimension:
                                            logger.info(f"Found matching dimension with fallback model {fallback_model}")
                                            query_embedding = fallback_embedding
                                            break
                                        else:
                                            logger.info(f"Fallback model {fallback_model} dimension: " +
                                                      f"{len(fallback_embedding)}, need: {collection_dimension}")
                                    except Exception as fallback_error:
                                        logger.warning(f"Error with fallback model {fallback_model}: {str(fallback_error)}")
                        except Exception as e:
                            logger.error(f"Error creating dimension-matched embedding: {str(e)}")
                            # 继续使用原始向量，让Chroma处理错误
                    
                    # 最后检查维度是否匹配
                    if len(query_embedding) != collection_dimension:
                        logger.error(f"Failed to create embedding with matching dimension. " +
                                   f"Using dimension {len(query_embedding)}, but collection requires {collection_dimension}")
                        # 这里不返回错误，而是让Chroma API处理，因为这是最清晰的错误信息来源
                
                # 增加n_results以确保有足够的结果
                expanded_top_k = top_k * 3
                logger.info(f"Increasing n_results to {expanded_top_k} for more candidates")
                
                # 查询参数，添加更多调试信息
                logger.info(f"Final query params: embedding dims={len(query_embedding)}, n_results={expanded_top_k}")
                
                # 执行不带过滤条件的搜索
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=expanded_top_k,
                    include=["metadatas", "documents", "distances"]
                )
                
                # 记录关键结果数据
                if results:
                    ids_count = len(results.get("ids", [[]])[0]) if len(results.get("ids", [])) > 0 else 0
                    docs_count = len(results.get("documents", [[]])[0]) if len(results.get("documents", [])) > 0 else 0
                    distances_count = len(results.get("distances", [[]])[0]) if len(results.get("distances", [])) > 0 else 0
                    
                    logger.info(f"Raw result counts - IDs: {ids_count}, Documents: {docs_count}, Distances: {distances_count}")
                else:
                    logger.warning("No results returned from Chroma")
                
                # 如果需要过滤结果，我们将在后处理中进行
                logger.info(f"Successfully executed search, processing results")
            except Exception as e:
                logger.error(f"Error executing search: {str(e)}")
                # 记录更多关于查询向量的信息
                if 'query_embedding' in locals():
                    logger.info(f"Query embedding: length={len(query_embedding)}, first few values={query_embedding[:5]}")
                return {
                    "results": [],
                    "error": f"Search failed: {str(e)}"
                }
            
            # 处理结果
            processed_results = []
            if results and len(results["ids"]) > 0 and len(results["ids"][0]) > 0:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]
                
                logger.info(f"Raw search results count: {len(documents)}")
                logger.info(f"Original threshold: {threshold}, Original word_count_threshold: {word_count_threshold}")
                
                # 如果结果为空，可能是阈值太高，降低阈值
                if threshold > 0.2:
                    actual_threshold = 0.2
                    logger.info(f"Reducing threshold to {actual_threshold} to find more results")
                else:
                    actual_threshold = threshold
                
                # 如果word_count_threshold设置太高，可能导致无结果，降低它
                actual_word_threshold = 0
                logger.info(f"Ignoring word count threshold for Chroma results")
                
                for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
                    # 计算余弦相似度（Chroma返回的是距离，需要转换为相似度）
                    # 相似度 = 1 - 距离
                    similarity = 1.0 - distance
                    
                    # 获取词数并确保其是数字
                    word_count = metadata.get("word_count", 0)
                    if isinstance(word_count, str):
                        try:
                            word_count = int(word_count)
                        except (ValueError, TypeError):
                            word_count = 0
                    
                    logger.info(f"Result {i+1} - Score: {similarity}, Word Count: {word_count}, Content: {doc[:100]}...")
                    
                    # 应用更宽松的过滤条件
                    if similarity >= actual_threshold:
                        processed_results.append({
                            "text": doc,
                            "score": float(similarity),
                            "metadata": {
                                "source": metadata.get("document_name", ""),
                                "page": metadata.get("page_number", ""),
                                "chunk": metadata.get("chunk_id", 0),
                                "total_chunks": metadata.get("total_chunks", 0),
                                "page_range": metadata.get("page_range", ""),
                                "embedding_provider": metadata.get("embedding_provider", ""),
                                "embedding_model": metadata.get("embedding_model", ""),
                                "embedding_timestamp": metadata.get("embedding_timestamp", "")
                            }
                        })
                        logger.info(f"Added result {i+1} to processed results (score: {similarity})")
                    else:
                        logger.info(f"Skipped result {i+1} due to low score: {similarity} < {actual_threshold}")
                
                logger.info(f"Total processed results after filtering: {len(processed_results)}")
                
                # 如果过滤后仍然没有结果，尝试返回至少一个最佳匹配
                if not processed_results and len(documents) > 0:
                    logger.warning("No results pass threshold filter, adding best match regardless of score")
                    best_idx = 0
                    for i, distance in enumerate(distances):
                        if distance < distances[best_idx]:
                            best_idx = i
                    
                    doc = documents[best_idx]
                    metadata = metadatas[best_idx]
                    similarity = 1.0 - distances[best_idx]
                    
                    processed_results.append({
                        "text": doc,
                        "score": float(similarity),
                        "metadata": {
                            "source": metadata.get("document_name", ""),
                            "page": metadata.get("page_number", ""),
                            "chunk": metadata.get("chunk_id", 0),
                            "total_chunks": metadata.get("total_chunks", 0),
                            "page_range": metadata.get("page_range", ""),
                            "embedding_provider": metadata.get("embedding_provider", ""),
                            "embedding_model": metadata.get("embedding_model", ""),
                            "embedding_timestamp": metadata.get("embedding_timestamp", ""),
                            "note": "Best match (below threshold)"
                        }
                    })
                    logger.info(f"Added best match with score {similarity} despite being below threshold")
            else:
                if not results:
                    logger.warning("No results returned from Chroma search")
                elif len(results["ids"]) == 0:
                    logger.warning("Results returned but ids array is empty")
                elif len(results["ids"][0]) == 0:
                    logger.warning("Results returned but first ids array is empty")
                    
                # 记录完整的结果结构，帮助调试
                logger.info(f"Raw results structure: {results}")
            
            response_data = {"results": processed_results}
            
            # 保存逻辑
            if save_results and processed_results:
                try:
                    # 使用原始的collection_id来保存结果，确保文件名兼容
                    filepath = self.save_search_results(query, original_collection_id, processed_results)
                    response_data["saved_filepath"] = filepath
                except Exception as e:
                    logger.error(f"Error saving search results: {str(e)}")
            
            return response_data
                
        except Exception as e:
            logger.error(f"Error in _search_chroma: {str(e)}", exc_info=True)
            return {
                "results": [],
                "error": f"Search failed: {str(e)}"
            }

    def _sanitize_collection_name(self, name: str) -> str:
        """
        清理和标准化集合名称，确保它适用于数据库
        
        Args:
            name: 原始集合名称
            
        Returns:
            str: 清理后的集合名称
        """
        if not isinstance(name, str):
            name = str(name)
        
        # 移除前后空格
        name = name.strip()
        
        # 移除任何不安全的字符
        name = re.sub(r'[^\w\-_]', '_', name)
        
        # 确保名称不为空
        if not name:
            name = "default_collection"
            
        return name 