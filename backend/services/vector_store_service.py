import os
from datetime import datetime
import json
from typing import List, Dict, Any
import logging
from pathlib import Path
import re
from pymilvus import connections, utility
from pymilvus import Collection, DataType, FieldSchema, CollectionSchema
from utils.config import VectorDBProvider, MILVUS_CONFIG, CHROMA_CONFIG  # 更新导入

logger = logging.getLogger(__name__)

class VectorDBConfig:
    """
    向量数据库配置类，用于存储和管理向量数据库的配置信息
    """
    def __init__(self, provider: str, index_mode: str):
        """
        初始化向量数据库配置
        
        参数:
            provider: 向量数据库提供商名称
            index_mode: 索引模式
        """
        self.provider = provider
        self.index_mode = index_mode
        self._config = self._get_db_config()

    def _get_db_config(self) -> Dict[str, Any]:
        """
        根据提供商获取对应的数据库配置
        
        返回:
            数据库配置字典
        """
        if self.provider == VectorDBProvider.MILVUS.value:
            return MILVUS_CONFIG
        elif self.provider == VectorDBProvider.CHROMA.value:
            return CHROMA_CONFIG
        else:
            raise ValueError(f"Unsupported vector database provider: {self.provider}")

    @property
    def uri(self) -> str:
        """
        获取数据库URI
        
        返回:
            数据库URI字符串
        """
        return self._config["uri"]

    def get_index_type(self) -> str:
        """
        根据索引模式获取索引类型
        
        返回:
            对应的索引类型
        """
        return self._config["index_types"].get(self.index_mode, "FLAT")
    
    def get_index_params(self) -> Dict[str, Any]:
        """
        根据索引模式获取索引参数
        
        返回:
            对应的索引参数字典
        """
        return self._config["index_params"].get(self.index_mode, {})

class VectorStoreService:
    """
    向量存储服务类，提供向量数据的索引、查询和管理功能
    """
    def __init__(self):
        """
        初始化向量存储服务
        """
        self.initialized_dbs = {}
        # 确保所有必要的存储目录存在
        os.makedirs("03-vector-store", exist_ok=True)
        
        # 记录基础路径
        self.base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        logger.info(f"Vector store base path: {self.base_path}")

    def _get_absolute_path(self, relative_path: str) -> str:
        """
        获取绝对路径
        
        参数:
            relative_path: 相对路径
             
        返回:
            绝对路径
        """
        return os.path.join(self.base_path, relative_path)

    def _sanitize_collection_name(self, name: str, for_provider: str = None) -> str:
        """
        清理集合名称，移除或替换非法字符
        
        参数:
            name: 原始名称
            for_provider: 指定数据库提供商，不同提供商有不同的命名规则
            
        返回:
            清理后的名称
        """
        # 将中文字符替换为下划线
        name = re.sub(r'[\u4e00-\u9fff]', '_', name)
        
        if for_provider == VectorDBProvider.MILVUS.value:
            # Milvus只允许字母、数字和下划线
            name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        else:
            # 一般情况下允许字母、数字、下划线和连字符
            name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
        
        # 将连续的下划线替换为单个下划线
        name = re.sub(r'_+', '_', name)
        # 移除开头和结尾的下划线和连字符
        name = name.strip('_-')
        
        # 确保名称以字母或数字开头和结尾(Chroma要求)
        if name and not name[0].isalnum():
            name = 'c' + name
        if name and not name[-1].isalnum():
            name = name + '0'
            
        # 确保名称不为空
        if not name:
            name = 'collection'
            
        # 确保名称长度在3-63之间(Chroma要求)
        if len(name) < 3:
            name = name + '_collection'[:3-len(name)]
        if len(name) > 63:
            name = name[:60] + 'xyz'
            
        return name

    def _sanitize_chroma_collection_name(self, name: str) -> str:
        """
        为Chroma数据库清理集合名称，确保符合其严格要求
        
        参数:
            name: 原始名称
            
        返回:
            符合Chroma要求的名称
        """
        # 基本清理
        name = self._sanitize_collection_name(name)
        
        # Chroma特定要求：
        # 1. 只允许字母、数字、下划线和连字符
        name = re.sub(r'[^a-zA-Z0-9_\-]', '', name)
        
        # 2. 必须以字母或数字开头和结尾
        if name and not name[0].isalnum():
            name = 'c' + name[1:] if len(name) > 1 else 'collection'
        if name and not name[-1].isalnum():
            name = name[:-1] + '0' if len(name) > 1 else 'collection0'
            
        # 3. 长度必须在3-63之间
        if len(name) < 3:
            name = name + 'col'[:3-len(name)]
        if len(name) > 63:
            name = name[:60] + 'end'
            
        # 4. 不能有连续的句点
        name = re.sub(r'\.\.+', '_', name)
        
        # 5. 不能是有效的IPv4地址
        if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', name):
            name = 'ip_' + name
            
        return name

    def _get_milvus_index_type(self, config: VectorDBConfig) -> str:
        """
        从配置对象获取索引类型
        
        参数:
            config: 向量数据库配置对象
            
        返回:
            索引类型
        """
        return config.get_index_type()
    
    def _get_milvus_index_params(self, config: VectorDBConfig) -> Dict[str, Any]:
        """
        从配置对象获取索引参数
        
        参数:
            config: 向量数据库配置对象
            
        返回:
            索引参数字典
        """
        return config.get_index_params()
    
    def index_embeddings(self, embedding_file: str, config: VectorDBConfig) -> Dict[str, Any]:
        """
        将嵌入向量索引到向量数据库
        
        参数:
            embedding_file: 嵌入向量文件路径
            config: 向量数据库配置对象
            
        返回:
            索引结果信息字典
        """
        start_time = datetime.now()
        result = {"index_size": 0, "collection_name": ""}
        
        try:
            logger.info(f"Starting indexing process for file: {embedding_file}")
            logger.info(f"Vector DB: {config.provider}, Index Mode: {config.index_mode}")
            
            # 确保目录存在
            self._ensure_db_dirs()
            
            # 读取embedding文件
            embeddings_data = self._load_embeddings(embedding_file)
            logger.info(f"Successfully loaded embeddings data with {len(embeddings_data.get('embeddings', []))} vectors")
            
            # 根据不同的数据库进行索引
            if config.provider == VectorDBProvider.MILVUS.value:
                result = self._index_to_milvus(embeddings_data, config)
            elif config.provider == VectorDBProvider.CHROMA.value:
                try:
                    import chromadb
                except ImportError:
                    raise ImportError("chromadb package is not installed. Please install it with 'pip install chromadb'")
                
                result = self._index_to_chroma(embeddings_data, config)
            else:
                raise ValueError(f"Unsupported vector database provider: {config.provider}")
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            response = {
                "database": config.provider,
                "index_mode": config.index_mode,
                "total_vectors": len(embeddings_data["embeddings"]),
                "index_size": result.get("index_size", 0),
                "processing_time": processing_time,
                "collection_name": result.get("collection_name", "")
            }
            
            logger.info(f"Indexing completed successfully: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error in index_embeddings: {str(e)}", exc_info=True)
            raise

    def _load_embeddings(self, file_path: str) -> Dict[str, Any]:
        """
        加载embedding文件，返回配置信息和embeddings
        
        参数:
            file_path: 嵌入向量文件路径
            
        返回:
            包含嵌入向量和元数据的字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loading embeddings from {file_path}")
                
                if not isinstance(data, dict) or "embeddings" not in data:
                    raise ValueError("Invalid embedding file format: missing 'embeddings' key")
                    
                # 返回完整的数据，包括顶层配置
                logger.info(f"Found {len(data['embeddings'])} embeddings")
                return data
                
        except Exception as e:
            logger.error(f"Error loading embeddings from {file_path}: {str(e)}")
            raise
    
    def _index_to_milvus(self, embeddings_data: Dict[str, Any], config: VectorDBConfig) -> Dict[str, Any]:
        """
        将嵌入向量索引到Milvus数据库
        
        参数:
            embeddings_data: 嵌入向量数据
            config: 向量数据库配置对象
            
        返回:
            索引结果信息字典
        """
        try:
            # 使用 filename 作为 collection 名称前缀
            filename = embeddings_data.get("filename", "")
            # 如果有 .pdf 后缀，移除它
            base_name = filename.replace('.pdf', '') if filename else "doc"
            
            # 清理集合名称，明确指定为Milvus提供商
            base_name = self._sanitize_collection_name(base_name, for_provider=VectorDBProvider.MILVUS.value)
            
            # 获取embedding provider
            embedding_provider = embeddings_data.get("embedding_provider", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            collection_name = f"{base_name}_{embedding_provider}_{timestamp}"
            
            # 再次确保最终的集合名称符合Milvus的要求
            collection_name = self._sanitize_collection_name(collection_name, for_provider=VectorDBProvider.MILVUS.value)
            
            logger.info(f"Final Milvus collection name: {collection_name}")
            
            # 连接到Milvus
            logger.info(f"Connecting to Milvus with URI: {config.uri}")
            connections.connect(
                alias="default",
                uri=config.uri,
                timeout=30  # 增加超时时间
            )
            
            # 从顶层配置获取向量维度
            vector_dim = int(embeddings_data.get("vector_dimension"))
            if not vector_dim:
                raise ValueError("Missing vector_dimension in embedding file")
            
            logger.info(f"Creating collection with dimension: {vector_dim}")
            
            # 定义字段
            fields = [
                {"name": "id", "dtype": "INT64", "is_primary": True, "auto_id": True},
                {"name": "content", "dtype": "VARCHAR", "max_length": 5000},
                {"name": "document_name", "dtype": "VARCHAR", "max_length": 255},
                {"name": "chunk_id", "dtype": "INT64"},
                {"name": "total_chunks", "dtype": "INT64"},
                {"name": "word_count", "dtype": "INT64"},
                {"name": "page_number", "dtype": "VARCHAR", "max_length": 10},
                {"name": "page_range", "dtype": "VARCHAR", "max_length": 10},
                # {"name": "chunking_method", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_provider", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_model", "dtype": "VARCHAR", "max_length": 50},
                {"name": "embedding_timestamp", "dtype": "VARCHAR", "max_length": 50},
                {
                    "name": "vector",
                    "dtype": "FLOAT_VECTOR",
                    "dim": vector_dim,
                    "params": self._get_milvus_index_params(config)
                }
            ]
            
            # 准备数据为列表格式
            entities = []
            for emb in embeddings_data["embeddings"]:
                entity = {
                    "content": str(emb["metadata"].get("content", "")),
                    "document_name": embeddings_data.get("filename", ""),  # 使用 filename 而不是 document_name
                    "chunk_id": int(emb["metadata"].get("chunk_id", 0)),
                    "total_chunks": int(emb["metadata"].get("total_chunks", 0)),
                    "word_count": int(emb["metadata"].get("word_count", 0)),
                    "page_number": str(emb["metadata"].get("page_number", 0)),
                    "page_range": str(emb["metadata"].get("page_range", "")),
                    # "chunking_method": str(emb["metadata"].get("chunking_method", "")),
                    "embedding_provider": embeddings_data.get("embedding_provider", ""),  # 从顶层配置获取
                    "embedding_model": embeddings_data.get("embedding_model", ""),  # 从顶层配置获取
                    "embedding_timestamp": str(emb["metadata"].get("embedding_timestamp", "")),
                    "vector": [float(x) for x in emb.get("embedding", [])]
                }
                entities.append(entity)
            
            logger.info(f"Creating Milvus collection with sanitized name: {collection_name}")
            
            # 创建collection
            # field_schemas = [
            #     FieldSchema(name=field["name"], 
            #                dtype=getattr(DataType, field["dtype"]),
            #                is_primary="is_primary" in field and field["is_primary"],
            #                auto_id="auto_id" in field and field["auto_id"],
            #                max_length=field.get("max_length"),
            #                dim=field.get("dim"),
            #                params=field.get("params"))
            #     for field in fields
            # ]

            field_schemas = []
            for field in fields:
                extra_params = {}
                if field.get('max_length') is not None:
                    extra_params['max_length'] = field['max_length']
                if field.get('dim') is not None:
                    extra_params['dim'] = field['dim']
                if field.get('params') is not None:
                    extra_params['params'] = field['params']
                field_schema = FieldSchema(
                    name=field["name"], 
                    dtype=getattr(DataType, field["dtype"]),
                    is_primary=field.get("is_primary", False),
                    auto_id=field.get("auto_id", False),
                    **extra_params
                )
                field_schemas.append(field_schema)

            schema = CollectionSchema(fields=field_schemas, description=f"Collection for {collection_name}")
            collection = Collection(name=collection_name, schema=schema)
            
            # 插入数据
            logger.info(f"Inserting {len(entities)} vectors")
            insert_result = collection.insert(entities)
            
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": self._get_milvus_index_type(config),
                "params": self._get_milvus_index_params(config)
            }
            collection.create_index(field_name="vector", index_params=index_params)
            collection.load()
            
            return {
                "index_size": len(insert_result.primary_keys),
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"Error indexing to Milvus: {str(e)}")
            raise
        
        finally:
            try:
                connections.disconnect("default")
                logger.info("Successfully disconnected from Milvus")
            except Exception as e:
                logger.error(f"Error disconnecting from Milvus: {str(e)}")

    def _index_to_chroma(self, embeddings_data: Dict[str, Any], config: VectorDBConfig) -> Dict[str, Any]:
        """
        将嵌入向量索引到Chroma数据库
        
        参数:
            embeddings_data: 嵌入向量数据
            config: 向量数据库配置对象
            
        返回:
            索引结果信息字典
        """
        try:
            # 使用 filename 作为 collection 名称前缀
            filename = embeddings_data.get("filename", "")
            base_name = filename.replace('.pdf', '') if filename else "doc"
            
            # 获取embedding provider
            embedding_provider = embeddings_data.get("embedding_provider", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # 构建集合名称并使用Chroma特定的清理方法
            raw_collection_name = f"{base_name}_{embedding_provider}_{timestamp}"
            # 为Chroma特别处理集合名称
            collection_name = self._sanitize_chroma_collection_name(raw_collection_name)
            
            logger.info(f"Original collection name: {raw_collection_name}")
            logger.info(f"Sanitized collection name for Chroma: {collection_name}")

            # 实现Chroma的索引逻辑
            logger.info(f"Indexing to Chroma collection: {collection_name}")
            
            # 导入chromadb并初始化客户端
            try:
                import chromadb
                from chromadb.config import Settings
            except ImportError:
                logger.error("chromadb package is not installed")
                raise ImportError("chromadb package is not installed. Please install it with 'pip install chromadb'")
            
            # 确保Chroma目录存在
            chroma_path = self._get_absolute_path(CHROMA_CONFIG["uri"])
            os.makedirs(chroma_path, exist_ok=True)
            logger.info(f"Using Chroma path: {chroma_path}")
            
            # 创建客户端
            client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 检查是否已存在该集合，如果存在则删除（防止错误）
            try:
                existing_collections = client.list_collections()
                existing_collection_names = [c.name for c in existing_collections]
                
                if collection_name in existing_collection_names:
                    logger.warning(f"Collection {collection_name} already exists, deleting it")
                    client.delete_collection(collection_name)
            except Exception as e:
                logger.warning(f"Error checking existing collections: {str(e)}")
            
            # 创建集合
            logger.info(f"Creating Chroma collection: {collection_name}")
            collection = client.create_collection(
                name=collection_name,
                metadata={
                    "description": f"Collection for {base_name}",
                    "document_name": embeddings_data.get("filename", ""),
                    "embedding_model": embeddings_data.get("embedding_model", ""),
                    "embedding_provider": embedding_provider,
                    "vector_dimension": embeddings_data.get("vector_dimension", 0),
                    "created_at": datetime.now().isoformat()
                }
            )
            
            # 准备数据
            ids = []
            embeddings = []
            metadatas = []
            documents = []
            
            # 处理嵌入向量
            for i, emb in enumerate(embeddings_data["embeddings"]):
                # 准备ID - 确保ID是字符串且格式正确
                entry_id = f"doc_{i+1:05d}"
                ids.append(entry_id)
                
                # 准备向量
                embedding = [float(x) for x in emb.get("embedding", [])]
                embeddings.append(embedding)
                
                # 准备元数据
                chunk_id = emb["metadata"].get("chunk_id", 0)
                if not isinstance(chunk_id, int):
                    try:
                        chunk_id = int(chunk_id)
                    except (TypeError, ValueError):
                        chunk_id = i
                
                total_chunks = emb["metadata"].get("total_chunks", 0)
                if not isinstance(total_chunks, int):
                    try:
                        total_chunks = int(total_chunks)
                    except (TypeError, ValueError):
                        total_chunks = len(embeddings_data["embeddings"])
                
                word_count = emb["metadata"].get("word_count", 0)
                if not isinstance(word_count, int):
                    try:
                        word_count = int(word_count)
                    except (TypeError, ValueError):
                        word_count = 100
                
                metadata = {
                    "document_name": str(embeddings_data.get("filename", "")),
                    "chunk_id": chunk_id,
                    "total_chunks": total_chunks,
                    "word_count": word_count,
                    "page_number": str(emb["metadata"].get("page_number", "0")),
                    "page_range": str(emb["metadata"].get("page_range", "")),
                    "embedding_provider": str(embedding_provider),
                    "embedding_model": str(embeddings_data.get("embedding_model", "")),
                    "embedding_timestamp": str(emb["metadata"].get("embedding_timestamp", "")),
                }
                metadatas.append(metadata)
                
                # 准备文档内容
                documents.append(str(emb["metadata"].get("content", "")))
            
            # 添加数据到集合
            logger.info(f"Adding {len(ids)} items to Chroma collection {collection_name}")
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            
            logger.info(f"Successfully added {len(ids)} items to Chroma collection {collection_name}")
            
            return {
                "index_size": len(embeddings_data["embeddings"]),
                "collection_name": collection_name
            }
            
        except Exception as e:
            logger.error(f"Error indexing to Chroma: {str(e)}", exc_info=True)
            raise

    def _ensure_db_dirs(self):
        """
        确保所有数据库目录存在
        """
        os.makedirs("03-vector-store", exist_ok=True)

    def list_collections(self, provider: str) -> List[Dict[str, Any]]:
        """
        列出指定向量数据库中的所有集合
        
        参数:
            provider: 向量数据库提供商
            
        返回:
            集合信息列表
        """
        try:
            # 确保转换为小写字符串以进行一致的比较
            provider_str = str(provider).lower().strip()
            logger.info(f"Listing collections for provider: '{provider_str}'")
            
            if provider_str == VectorDBProvider.MILVUS.value.lower():
                # Milvus处理逻辑
                logger.info("Using Milvus to list collections")
                return self._list_milvus_collections()
            elif provider_str == VectorDBProvider.CHROMA.value.lower():
                # Chroma处理逻辑
                logger.info("Using Chroma to list collections")
                return self._list_chroma_collections()
            else:
                logger.error(f"Unsupported vector database provider: '{provider_str}'")
                return []
        except Exception as e:
            logger.error(f"Error in list_collections: {str(e)}")
            return []
            
    def _list_milvus_collections(self) -> List[Dict[str, Any]]:
        """列出Milvus中的所有集合"""
        try:
            logger.info(f"Connecting to Milvus at {MILVUS_CONFIG['uri']}")
            connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
            collections = []
            
            # 获取所有集合名称
            try:
                collection_names = utility.list_collections()
                logger.info(f"Found {len(collection_names)} collections in Milvus")
                
                # 获取每个集合的详细信息
                for name in collection_names:
                    try:
                        collection = Collection(name)
                        collection.load()
                        
                        # 获取实体数量
                        entity_count = collection.num_entities
                        
                        collections.append({
                            "id": name,
                            "name": name,
                            "count": entity_count,
                            "provider": VectorDBProvider.MILVUS.value
                        })
                    except Exception as e:
                        logger.error(f"Error getting info for collection {name}: {str(e)}")
                        collections.append({
                            "id": name,
                            "name": name,
                            "count": 0,
                            "provider": VectorDBProvider.MILVUS.value,
                            "error": str(e)
                        })
            except Exception as e:
                logger.error(f"Error listing Milvus collections: {str(e)}")
                return []
                
            return collections
        except Exception as e:
            logger.error(f"Error connecting to Milvus: {str(e)}")
            return []
        finally:
            # 确保断开连接
            try:
                connections.disconnect("default")
                logger.info("Disconnected from Milvus")
            except Exception as disconnect_error:
                logger.error(f"Error disconnecting from Milvus: {str(disconnect_error)}")
    
    def _list_chroma_collections(self) -> List[Dict[str, Any]]:
        """列出Chroma中的所有集合"""
        try:
            # 导入chromadb
            import chromadb
            from chromadb.config import Settings
            
            # 获取Chroma路径
            chroma_path = self._get_absolute_path(CHROMA_CONFIG["uri"])
            logger.info(f"Connecting to Chroma at {chroma_path}")
            
            # 确保目录存在
            os.makedirs(chroma_path, exist_ok=True)
            
            # 创建客户端
            client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取所有集合
            chroma_collections = client.list_collections()
            logger.info(f"Found {len(chroma_collections)} collections in Chroma")
            
            # 转换为统一的返回格式
            collections = []
            for col in chroma_collections:
                try:
                    count = col.count()
                    collections.append({
                        "id": col.name,
                        "name": col.name,
                        "count": count,
                        "provider": VectorDBProvider.CHROMA.value
                    })
                except Exception as e:
                    logger.error(f"Error getting count for collection {col.name}: {str(e)}")
                    collections.append({
                        "id": col.name,
                        "name": col.name,
                        "count": 0,
                        "provider": VectorDBProvider.CHROMA.value,
                        "error": str(e)
                    })
            
            return collections
        except ImportError as e:
            logger.error(f"ChromaDB package is not installed: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error listing Chroma collections: {str(e)}")
            return []

    def delete_collection(self, provider: str, collection_name: str) -> bool:
        """
        删除指定的集合
        
        参数:
            provider: 向量数据库提供商
            collection_name: 集合名称
            
        返回:
            是否删除成功
        """
        try:
            logger.info(f"Attempting to delete collection: {collection_name} from provider: {provider}")
            
            if provider == VectorDBProvider.MILVUS.value:
                try:
                    connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                    utility.drop_collection(collection_name)
                    logger.info(f"Successfully deleted Milvus collection: {collection_name}")
                    return True
                except Exception as e:
                    logger.error(f"Error deleting Milvus collection {collection_name}: {str(e)}")
                    raise
                finally:
                    connections.disconnect("default")
                    
            elif provider == VectorDBProvider.CHROMA.value:
                try:
                    # 导入chromadb
                    import chromadb
                    from chromadb.config import Settings
                    
                    # 获取Chroma路径
                    chroma_path = self._get_absolute_path(CHROMA_CONFIG["uri"])
                    logger.info(f"Deleting Chroma collection from path: {chroma_path}")
                    
                    # 创建客户端
                    client = chromadb.PersistentClient(
                        path=chroma_path,
                        settings=Settings(anonymized_telemetry=False)
                    )
                    
                    # 获取所有集合以验证请求的集合是否存在
                    collections = client.list_collections()
                    collection_names = [c.name for c in collections]
                    
                    if collection_name not in collection_names:
                        logger.warning(f"Collection {collection_name} not found in Chroma database")
                        # 尝试寻找相似名称的集合
                        for name in collection_names:
                            if collection_name in name or name in collection_name:
                                logger.info(f"Found similar collection name: {name}")
                                collection_name = name
                                break
                    
                    # 删除集合
                    logger.info(f"Deleting Chroma collection: {collection_name}")
                    client.delete_collection(name=collection_name)
                    logger.info(f"Successfully deleted Chroma collection: {collection_name}")
                    return True
                    
                except ImportError as e:
                    logger.error(f"ChromaDB package is not installed: {str(e)}")
                    raise ImportError("ChromaDB package is not installed")
                except Exception as e:
                    logger.error(f"Error deleting Chroma collection {collection_name}: {str(e)}")
                    raise
                
            else:
                logger.error(f"Unsupported vector database provider: {provider}")
                raise ValueError(f"Unsupported vector database provider: {provider}")
            
        except Exception as e:
            logger.error(f"Error in delete_collection: {str(e)}")
            raise

    def get_collection_info(self, provider: str, collection_name: str) -> Dict[str, Any]:
        """
        获取指定集合的信息
        
        参数:
            provider: 向量数据库提供商
            collection_name: 集合名称
            
        返回:
            集合信息字典
        """
        logger.info(f"Getting collection info for provider: {provider}, collection: {collection_name}")
        
        if provider == VectorDBProvider.MILVUS.value:
            try:
                connections.connect(alias="default", uri=MILVUS_CONFIG["uri"])
                collection = Collection(collection_name)
                info = {
                    "name": collection_name,
                    "num_entities": collection.num_entities,
                    "schema": collection.schema.to_dict()
                }
                logger.info(f"Successfully retrieved Milvus collection info: {collection_name}")
                return info
            except Exception as e:
                logger.error(f"Error getting Milvus collection info: {str(e)}")
                raise
            finally:
                connections.disconnect("default")
                
        elif provider == VectorDBProvider.CHROMA.value:
            try:
                # 导入chromadb
                import chromadb
                from chromadb.config import Settings
                
                # 获取Chroma路径
                chroma_path = self._get_absolute_path(CHROMA_CONFIG["uri"])
                logger.info(f"Getting Chroma collection info from path: {chroma_path}")
                
                # 创建客户端
                client = chromadb.PersistentClient(
                    path=chroma_path,
                    settings=Settings(anonymized_telemetry=False)
                )
                
                # 获取指定集合
                collection = client.get_collection(name=collection_name)
                
                # 获取集合元数据
                metadata = collection.metadata
                logger.info(f"Collection metadata: {metadata}")
                
                # 获取文档数量
                count = collection.count()
                
                # 获取一些示例文档
                sample = None
                try:
                    # 尝试获取一个样本文档来展示结构
                    sample_result = collection.peek(limit=1)
                    if sample_result and len(sample_result['ids']) > 0:
                        sample = {
                            "ids": sample_result['ids'],
                            "metadatas": sample_result['metadatas']
                        }
                except Exception as e:
                    logger.warning(f"Could not retrieve sample document: {str(e)}")
                
                info = {
                    "name": collection_name,
                    "num_entities": count,
                    "metadata": metadata or {},
                    "sample": sample
                }
                
                logger.info(f"Successfully retrieved Chroma collection info: {collection_name}")
                return info
                
            except ImportError as e:
                logger.error(f"ChromaDB package is not installed: {str(e)}")
                return {"error": "ChromaDB package is not installed"}
            except Exception as e:
                logger.error(f"Error getting Chroma collection info: {str(e)}")
                return {"error": str(e)}
        
        else:
            logger.error(f"Unsupported vector database provider: {provider}")
            raise ValueError(f"Unsupported vector database provider: {provider}")