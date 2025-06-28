import os
import json
from datetime import datetime
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Body,
    Query,
    Request,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from services.chunking_service import ChunkingService
from services.embedding_service import EmbeddingService, EmbeddingConfig
from services.vector_store_service import VectorStoreService, VectorDBConfig
from services.search_service import SearchService
from services.parsing_service import ParsingService
from services.loading_service import LoadingService
import logging
from enum import Enum
from utils.config import VectorDBProvider
import pandas as pd
from pathlib import Path
from services.generation_service import GenerationService
from typing import List, Dict, Optional
from utils.logger import logger
from fastapi.responses import JSONResponse

# 设置日志
os.makedirs("logs", exist_ok=True)
app = FastAPI(
    title="RAG框架后端API",
    description="用于文档处理、向量化、搜索和生成的完整RAG系统",
    version="1.0.0"
)

# 确保必要的目录存在
os.makedirs("temp", exist_ok=True)
os.makedirs("01-chunked-docs", exist_ok=True)
os.makedirs("02-embedded-docs", exist_ok=True)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("=== RAG System Backend Starting ===")
    logger.info("FastAPI application is starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI application is shutting down...")
    logger.info("=== RAG System Backend Stopped ===")


@app.post("/process")
async def process_file(
    file: UploadFile = File(...),
    loading_method: str = Form(...),
    chunking_option: str = Form(...),
    chunk_size: int = Form(1000),
):
    """
    处理上传的文件（PDF等）
    
    功能：上传文件并进行加载和分块处理
    
    参数：
    - file: 上传的文件（支持PDF等格式）
    - loading_method: 加载方法（如pymupdf、pdfplumber等）
    - chunking_option: 分块选项（如semantic、fixed_size等）
    - chunk_size: 分块大小（默认1000字符）
    
    返回：
    - chunks: 分块后的文档内容列表
    """
    try:
        # 创建临时目录（如果不存在）
        os.makedirs("temp", exist_ok=True)

        # 保存上传的文件
        temp_path = os.path.join("temp", file.filename)
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 准备元数据
        metadata = {
            "filename": file.filename,
            "loading_method": loading_method,
            "original_file_size": len(content),
            "processing_date": datetime.now().isoformat(),
            "chunking_method": chunking_option,
        }

        loading_service = LoadingService()
        raw_text = loading_service.load_pdf(temp_path, loading_method)
        metadata["total_pages"] = loading_service.get_total_pages()

        page_map = loading_service.get_page_map()

        chunking_service = ChunkingService()
        chunks = chunking_service.chunk_text(
            raw_text,
            chunking_option,
            metadata,
            page_map=page_map,
            chunk_size=chunk_size,
        )

        # 清理临时文件
        os.remove(temp_path)

        return {"chunks": chunks}
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise


@app.post("/save")
async def save_chunks(data: dict):
    """
    保存分块后的文档
    
    功能：将处理后的文档块保存到01-chunked-docs目录
    
    参数：
    - docName: 文档名称
    - chunks: 文档块列表
    - metadata: 元数据信息
    
    返回：
    - status: 保存状态
    - message: 状态消息
    - filepath: 保存的文件路径
    """
    try:
        doc_name = data.get("docName")
        chunks = data.get("chunks")
        metadata = data.get("metadata", {})

        if not doc_name or not chunks:
            raise ValueError("Missing required fields")

        # 构建文件名
        filename = f"{doc_name}.json"
        filepath = os.path.join("01-chunked-docs", filename)

        # 保存数据
        document_data = {
            "document_name": doc_name,
            "metadata": metadata,
            "chunks": chunks,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(document_data, f, ensure_ascii=False, indent=2)

        return {
            "status": "success",
            "message": "Document saved successfully",
            "filepath": filepath,
        }
    except Exception as e:
        logger.error(f"Error saving document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list-docs")
async def list_documents():
    """
    获取已分块文档列表
    
    功能：列出01-chunked-docs目录中的所有已保存文档
    
    返回：
    - documents: 文档列表，包含id和name
    """
    try:
        docs = []
        docs_dir = "01-chunked-docs"
        for filename in os.listdir(docs_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(docs_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    doc_data = json.load(f)
                    docs.append({"id": filename, "name": doc_data["document_name"]})
        return {"documents": docs}
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise


@app.post("/embed")
async def embed_document(data: dict = Body(...)):
    """
    对文档进行向量化嵌入
    
    功能：使用指定的嵌入模型对文档进行向量化处理
    
    参数：
    - documentId: 文档ID
    - provider: 嵌入服务提供商（如openai、huggingface等）
    - model: 嵌入模型名称
    
    返回：
    - status: 处理状态
    - message: 状态消息
    - filepath: 嵌入文件保存路径
    - embeddings: 生成的向量嵌入
    """
    try:
        doc_id = data.get("documentId")
        provider = data.get("provider")
        model = data.get("model")

        if not all([doc_id, provider, model]):
            raise HTTPException(status_code=400, detail="Missing required parameters")

        # 查找文档路径，增加对parsed-docs的支持
        loaded_path = os.path.join("01-loaded-docs", doc_id)
        chunked_path = os.path.join("01-chunked-docs", doc_id)
        parsed_path = os.path.join("01-parsed-docs", doc_id)

        doc_path = None
        doc_type = None
        if os.path.exists(loaded_path):
            doc_path = loaded_path
            doc_type = "loaded"
        elif os.path.exists(chunked_path):
            doc_path = chunked_path
            doc_type = "chunked"
        elif os.path.exists(parsed_path):
            doc_path = parsed_path
            doc_type = "parsed"

        if not doc_path:
            raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

        with open(doc_path, "r", encoding="utf-8") as f:
            doc_data = json.load(f)

        # 创建 EmbeddingConfig 和 EmbeddingService
        config = EmbeddingConfig(provider=provider, model_name=model)
        embedding_service = EmbeddingService()

        # 根据文档类型准备不同的输入数据
        if doc_type == "parsed":
            # 解析文档格式处理
            chunks = []
            for idx, item in enumerate(doc_data.get("content", [])):
                # 跳过没有内容的项
                if not item.get("content"):
                    continue

                chunk = {
                    "content": item.get("content", ""),
                    "metadata": {
                        "chunk_id": idx + 1,
                        "page_number": item.get("page", 1),
                        "page_range": str(item.get("page", 1)),
                        "word_count": (
                            len(item.get("content", "").split())
                            if item.get("content")
                            else 0
                        ),
                    },
                }
                chunks.append(chunk)

            # 如果没有有效的内容块，抛出异常
            if not chunks:
                raise HTTPException(
                    status_code=400, detail="No valid content found in the document"
                )

            # 计算文档的总页数（取最大页码）
            max_page = 1
            for item in doc_data.get("content", []):
                if item.get("page", 1) > max_page:
                    max_page = item.get("page", 1)

            input_data = {
                "chunks": chunks,
                "metadata": {
                    "filename": doc_data.get("metadata", {}).get("filename", doc_id),
                    "total_chunks": len(chunks),
                    "total_pages": max_page,
                    "loading_method": "unstructured",
                    "chunking_method": doc_data.get("metadata", {}).get(
                        "parsing_method", "parsed"
                    ),
                },
            }
        else:
            # 已加载和已分块文档的原有处理方式
            input_data = {
                "chunks": doc_data["chunks"],
                "metadata": {
                    "filename": doc_data["filename"],
                    "total_chunks": doc_data["total_chunks"],
                    "total_pages": doc_data["total_pages"],
                    "loading_method": doc_data.get("loading_method", "unknown"),
                    "chunking_method": doc_data.get("chunking_method", "unknown"),
                },
            }

        # 创建嵌入 - 只接收两个返回值
        embeddings, _ = embedding_service.create_embeddings(input_data, config)

        # 保存嵌入结果
        output_path = embedding_service.save_embeddings(doc_id, embeddings)

        return {
            "status": "success",
            "message": "Embeddings created successfully",
            "filepath": output_path,
            "embeddings": embeddings,  # 添加embeddings到响应中
        }

    except Exception as e:
        logger.error(f"Error creating embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list-embedded")
async def list_embedded_docs():
    """
    获取已嵌入文档列表
    
    功能：列出02-embedded-docs目录中的所有已向量化文档
    
    返回：
    - documents: 嵌入文档列表，包含名称和元数据信息
      - name: 文件名
      - metadata: 包含嵌入模型、提供商、时间戳等信息
    """
    try:
        documents = []
        embedded_dir = "02-embedded-docs"
        logger.info(f"Scanning directory: {embedded_dir}")

        if not os.path.exists(embedded_dir):
            logger.warning(f"Directory {embedded_dir} does not exist")
            return {"documents": []}

        for filename in os.listdir(embedded_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(embedded_dir, filename)
                logger.info(f"Reading file: {file_path}")
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # 获取时间戳，用于排序
                        timestamp = data.get("created_at", "")
                        # 使用实际的文件名，而不是文档名
                        doc_info = {
                            "name": filename,  # 保持原始文件名
                            "metadata": {
                                "document_name": data.get("document_name", filename),
                                "embedding_model": data.get("embedding_model", ""),
                                "embedding_provider": data.get(
                                    "embedding_provider", ""
                                ),
                                "embedding_timestamp": timestamp,
                                "vector_dimension": data.get("vector_dimension", 0),
                            },
                            "_timestamp_for_sorting": timestamp,  # 添加用于排序的隐藏字段
                        }
                        logger.info(f"Added document info: {doc_info}")
                        documents.append(doc_info)
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")

        # 按时间戳倒序排序（最新的排在前面）
        documents.sort(key=lambda x: x.get("_timestamp_for_sorting", ""), reverse=True)

        # 移除用于排序的临时字段
        for doc in documents:
            if "_timestamp_for_sorting" in doc:
                del doc["_timestamp_for_sorting"]

        logger.info(f"Total documents found: {len(documents)}")
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing embedded documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index")
async def index_embeddings(data: dict):
    """
    将向量嵌入索引到向量数据库
    
    功能：将生成的向量嵌入存储到指定的向量数据库中
    
    参数：
    - fileId: 嵌入文件ID
    - vectorDb: 向量数据库类型（如milvus、chroma等）
    - indexMode: 索引模式
    
    返回：
    - 索引操作结果信息
    """
    try:
        file_id = data.get("fileId")
        vector_db = data.get("vectorDb")
        index_mode = data.get("indexMode")

        if not all([file_id, vector_db, index_mode]):
            raise ValueError("Missing required fields")

        embedding_file = os.path.join("02-embedded-docs", file_id)
        if not os.path.exists(embedding_file):
            raise FileNotFoundError(f"Embedding file not found: {file_id}")

        config = VectorDBConfig(provider=vector_db, index_mode=index_mode)
        vector_store_service = VectorStoreService()
        result = vector_store_service.index_embeddings(embedding_file, config)

        return result
    except Exception as e:
        logger.error(f"Error during indexing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/providers")
async def get_providers():
    """
    获取支持的向量数据库提供商列表
    
    功能：返回系统支持的所有向量数据库类型
    
    返回：
    - providers: 支持的向量数据库提供商列表
    """
    try:
        search_service = SearchService()
        providers = search_service.get_providers()
        return {"providers": providers}
    except Exception as e:
        logger.error(f"Error getting providers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections")
async def get_collections(
    provider: VectorDBProvider = Query(default=VectorDBProvider.MILVUS),
):
    """
    获取指定向量数据库中的集合列表
    
    功能：列出指定向量数据库中的所有集合
    
    参数：
    - provider: 向量数据库提供商（默认为MILVUS）
    
    返回：
    - collections: 集合列表
    """
    try:
        search_service = SearchService()
        collections = search_service.list_collections(provider.value)
        return {"collections": collections}
    except Exception as e:
        logger.error(f"Error getting collections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_with_query_param(
    body: dict = Body(...), provider: str = Query(None)  # 添加URL查询参数
):
    """
    执行向量相似性搜索（通过查询参数）
    
    功能：在指定的向量数据库集合中执行相似性搜索
    
    参数：
    - query: 搜索查询文本
    - collection_id: 集合ID
    - provider: 向量数据库提供商（可通过URL参数传递）
    - top_k: 返回结果数量（默认3）
    - threshold: 相似度阈值（默认0.5）
    - word_count_threshold: 最小字数阈值（默认30）
    - save_results: 是否保存搜索结果（默认false）
    
    返回：
    - results: 搜索结果列表，包含文本内容、元数据和相似度分数
    """
    try:
        # 从请求体中提取参数
        query = body.get("query", "")
        collection_id = body.get("collection_id", "")
        body_provider = body.get("provider", VectorDBProvider.MILVUS.value)
        top_k = body.get("top_k", 3)
        threshold = body.get("threshold", 0.5)  # 相似度阈值默认50%
        word_count_threshold = body.get("word_count_threshold", 30)  # 最小字数默认30
        save_results = body.get("save_results", False)

        # 优先使用URL中的提供商参数，其次是请求体中的提供商参数
        provider_str = provider or body_provider

        # Log the incoming search request details
        logger.info(
            f"Search request with query param - Raw Provider: {provider_str}, Query: {query}, Collection: {collection_id}, Top K: {top_k}, Threshold: {threshold}, Word Count Threshold: {word_count_threshold}"
        )

        # 验证集合ID是否为字符串
        if not isinstance(collection_id, str):
            collection_id = str(collection_id)
            logger.warning(f"Converted collection_id to string: {collection_id}")

        # 确保 provider_str 是字符串，而不是转换为枚举值
        if not isinstance(provider_str, str):
            provider_str = str(provider_str)

        # 规范化 provider 字符串 (确保为小写)
        provider_str = provider_str.lower().strip()
        logger.info(f"Normalized provider string: '{provider_str}'")

        # 严格验证 provider_str 是否为有效值
        valid_providers = [
            VectorDBProvider.MILVUS.value.lower(),
            VectorDBProvider.CHROMA.value.lower(),
        ]
        if provider_str not in valid_providers:
            logger.warning(
                f"Invalid provider: '{provider_str}', valid options are: {valid_providers}"
            )
            logger.warning(f"Defaulting to milvus")
            provider_str = VectorDBProvider.MILVUS.value

        logger.info(f"Using provider: '{provider_str}'")

        search_service = SearchService()

        # Log before calling the search function
        logger.info("Calling search service...")

        results = await search_service.search(
            provider=provider_str,  # 直接传递字符串，不转换为枚举值
            query=query,
            collection_id=collection_id,
            top_k=top_k,
            threshold=threshold,
            word_count_threshold=word_count_threshold,
            save_results=save_results,
        )

        # Log the search results
        logger.info(f"Search response: {results}")

        return {"results": results}
    except Exception as e:
        logger.error(f"Error performing search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{provider}")
async def get_provider_collections(provider: str):
    """
    获取特定向量数据库提供商的集合列表
    
    功能：获取指定提供商下的所有可用集合
    
    参数：
    - provider: 向量数据库提供商名称
    
    返回：
    - collections: 该提供商下的集合列表
    """
    try:
        vector_store_service = VectorStoreService()
        collections = vector_store_service.list_collections(provider)
        return {"collections": collections}
    except Exception as e:
        logger.error(f"Error getting collections for provider {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collections/{provider}/{collection_name}")
async def get_collection_info(provider: str, collection_name: str):
    """
    获取特定集合的详细信息
    
    功能：获取指定集合的元数据和统计信息
    
    参数：
    - provider: 向量数据库提供商名称
    - collection_name: 集合名称
    
    返回：
    - 集合的详细信息，包括文档数量、维度等
    """
    try:
        vector_store_service = VectorStoreService()
        info = vector_store_service.get_collection_info(provider, collection_name)
        return info
    except Exception as e:
        logger.error(f"Error getting collection info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collections/{provider}/{collection_name}")
async def delete_collection(provider: str, collection_name: str):
    """
    删除指定的集合
    
    功能：从向量数据库中删除指定的集合及其所有数据
    
    参数：
    - provider: 向量数据库提供商名称
    - collection_name: 要删除的集合名称
    
    返回：
    - message: 删除操作结果消息
    """
    try:
        vector_store_service = VectorStoreService()
        success = vector_store_service.delete_collection(provider, collection_name)
        if success:
            return {"message": f"Collection {collection_name} deleted successfully"}
        else:
            raise HTTPException(
                status_code=400, detail=f"Failed to delete collection {collection_name}"
            )
    except Exception as e:
        logger.error(f"Error deleting collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def get_documents(type: str = Query("all")):
    """
    获取不同阶段的文档列表
    
    功能：获取loaded、chunked、parsed等不同处理阶段的文档
    
    参数：
    - type: 文档类型（all/loaded/chunked/parsed，默认为all）
    
    返回：
    - documents: 文档列表，包含ID、名称、类型和元数据
    """
    try:
        documents = []

        # 读取loaded文档
        if type in ["all", "loaded"]:
            loaded_dir = "01-loaded-docs"
            if os.path.exists(loaded_dir):
                for filename in os.listdir(loaded_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(loaded_dir, filename)
                        with open(file_path, "r", encoding="utf-8") as f:
                            doc_data = json.load(f)
                            documents.append(
                                {
                                    "id": filename,
                                    "name": filename,
                                    "type": "loaded",
                                    "metadata": {
                                        "total_pages": doc_data.get("total_pages"),
                                        "total_chunks": doc_data.get("total_chunks"),
                                        "loading_method": doc_data.get(
                                            "loading_method"
                                        ),
                                        "chunking_method": doc_data.get(
                                            "chunking_method"
                                        ),
                                        "timestamp": doc_data.get("timestamp"),
                                    },
                                    "_timestamp_for_sorting": doc_data.get(
                                        "timestamp", ""
                                    ),  # 添加排序字段
                                }
                            )

        # 读取chunked文档
        if type in ["all", "chunked"]:
            chunked_dir = "01-chunked-docs"
            if os.path.exists(chunked_dir):
                for filename in os.listdir(chunked_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(chunked_dir, filename)
                        with open(file_path, "r", encoding="utf-8") as f:
                            doc_data = json.load(f)
                            documents.append(
                                {
                                    "id": filename,
                                    "name": filename,  # 保持原始文件名
                                    "type": "chunked",
                                    "metadata": {
                                        "total_pages": doc_data.get("total_pages"),
                                        "total_chunks": doc_data.get("total_chunks"),
                                        "loading_method": doc_data.get(
                                            "loading_method"
                                        ),
                                        "chunking_method": doc_data.get(
                                            "chunking_method"
                                        ),
                                        "timestamp": doc_data.get("timestamp"),
                                    },
                                    "_timestamp_for_sorting": doc_data.get(
                                        "timestamp", ""
                                    ),  # 添加排序字段
                                },
                            )

        # 读取parsed文档
        if type in ["all", "parsed"]:
            parsed_dir = "01-parsed-docs"
            if os.path.exists(parsed_dir):
                for filename in os.listdir(parsed_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(parsed_dir, filename)
                        with open(file_path, "r", encoding="utf-8") as f:
                            doc_data = json.load(f)
                            metadata = doc_data.get("metadata", {})
                            timestamp = metadata.get("timestamp", "")
                            documents.append(
                                {
                                    "id": filename,
                                    "name": filename,
                                    "type": "parsed",
                                    "metadata": {
                                        "filename": metadata.get("filename"),
                                        "filetype": metadata.get("filetype"),
                                        "filesize": metadata.get("filesize"),
                                        "total_elements": metadata.get(
                                            "total_elements"
                                        ),
                                        "parsing_method": metadata.get(
                                            "parsing_method"
                                        ),
                                        "timestamp": timestamp,
                                    },
                                    "_timestamp_for_sorting": timestamp,  # 添加排序字段
                                }
                            )

        # 按时间戳倒序排序（最新的排在前面）
        documents.sort(key=lambda x: x.get("_timestamp_for_sorting", ""), reverse=True)

        # 移除用于排序的临时字段
        for doc in documents:
            if "_timestamp_for_sorting" in doc:
                del doc["_timestamp_for_sorting"]

        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{doc_name}")
async def get_document(doc_name: str, type: str = Query("loaded")):
    """
    获取特定文档的详细内容
    
    功能：读取并返回指定文档的完整内容和元数据
    
    参数：
    - doc_name: 文档名称
    - type: 文档类型（loaded/chunked/parsed，默认为loaded）
    
    返回：
    - 文档的完整内容和元数据信息
    """
    try:

        base_name = doc_name.replace(".json", "")
        file_name = f"{base_name}.json"

        # 根据类型选择不同的目录
        if type == "loaded":
            directory = "01-loaded-docs"
        elif type == "chunked":
            directory = "01-chunked-docs"
        elif type == "parsed":
            directory = "01-parsed-docs"
        else:
            directory = "01-loaded-docs"  # 默认目录
        file_path = os.path.join(directory, file_name)

        logger.info(f"Attempting to read document from: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"Document not found at path: {file_path}")
            raise HTTPException(status_code=404, detail="Document not found")

        with open(file_path, "r", encoding="utf-8") as f:
            doc_data = json.load(f)

        return doc_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{doc_name}")
async def delete_document(doc_name: str, type: str = Query("loaded")):
    """
    删除指定的文档
    
    功能：从指定目录中删除文档文件
    
    参数：
    - doc_name: 要删除的文档名称
    - type: 文档类型（loaded/chunked/parsed，默认为loaded）
    
    返回：
    - status: 删除状态
    - message: 操作结果消息
    """
    try:
        # 移除已有的 .json 扩展名（如果有）然后添加一个
        base_name = doc_name.replace(".json", "")
        file_name = f"{base_name}.json"

        # 根据类型选择不同的目录
        if type == "loaded":
            directory = "01-loaded-docs"
        elif type == "chunked":
            directory = "01-chunked-docs"
        elif type == "parsed":
            directory = "01-parsed-docs"
        else:
            directory = "01-loaded-docs"  # 默认目录
        file_path = os.path.join(directory, file_name)

        logger.info(f"Attempting to delete document: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"Document not found at path: {file_path}")
            raise HTTPException(status_code=404, detail="Document not found")

        # 删除文件
        os.remove(file_path)

        return {
            "status": "success",
            "message": f"Document {doc_name} deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/embedded-docs/{doc_name}")
async def get_embedded_doc(doc_name: str):
    """
    获取特定嵌入文档的详细内容
    
    功能：读取并返回指定嵌入文档的向量和元数据
    
    参数：
    - doc_name: 嵌入文档名称
    
    返回：
    - embeddings: 向量嵌入列表，包含向量数据和元数据
    """
    try:
        logger.info(f"Attempting to read document: {doc_name}")
        file_path = os.path.join("02-embedded-docs", doc_name)

        if not os.path.exists(file_path):
            logger.error(f"Document not found: {file_path}")
            raise HTTPException(
                status_code=404, detail=f"Document {doc_name} not found"
            )

        with open(file_path, "r", encoding="utf-8") as f:
            doc_data = json.load(f)
            logger.info(f"Successfully read document: {doc_name}")

            return {
                "embeddings": [
                    {
                        "embedding": embedding["embedding"],
                        "metadata": {
                            "document_name": doc_data.get("document_name", doc_name),
                            "chunk_id": idx + 1,
                            "total_chunks": len(doc_data["embeddings"]),
                            "content": embedding["metadata"].get("content", ""),
                            "page_number": embedding["metadata"].get("page_number", ""),
                            "page_range": embedding["metadata"].get("page_range", ""),
                            # "chunking_method": embedding["metadata"].get("chunking_method", ""),
                            "embedding_model": doc_data.get("embedding_model", ""),
                            "embedding_provider": doc_data.get(
                                "embedding_provider", ""
                            ),
                            "embedding_timestamp": doc_data.get("created_at", ""),
                            "vector_dimension": doc_data.get("vector_dimension", 0),
                        },
                    }
                    for idx, embedding in enumerate(doc_data["embeddings"])
                ]
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting embedded document {doc_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/embedded-docs/{doc_name}")
async def delete_embedded_doc(doc_name: str):
    """
    删除特定的嵌入文档
    
    功能：从02-embedded-docs目录中删除指定的嵌入文档
    
    参数：
    - doc_name: 要删除的嵌入文档名称
    
    返回：
    - message: 删除操作结果消息
    """
    try:
        file_path = os.path.join("02-embedded-docs", doc_name)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Document {doc_name} not found"
            )

        os.remove(file_path)
        return {"message": f"Document {doc_name} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting embedded document {doc_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse")
async def parse_file(
    file: UploadFile = File(...),
    parsing_option: str = Form("marker"),  # 默认使用marker，向后兼容
):
    """
    解析上传的文档文件
    
    功能：使用指定方法解析文档，提取结构化内容
    
    参数：
    - file: 上传的文件
    - parsing_option: 解析方法（默认为marker）
    
    返回：
    - 解析后的结构化文档内容
    """
    try:
        # 创建临时目录，如果不存在
        os.makedirs("temp", exist_ok=True)

        # 保存上传的文件
        temp_path = os.path.join("temp", file.filename)
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 准备元数据
        metadata = {
            "filename": file.filename,
            "filetype": os.path.splitext(file.filename)[1].lower(),
            "filesize": len(content),
            "processing_date": datetime.now().isoformat(),
        }

        # 使用新的ParsingService直接解析文档
        parsing_service = ParsingService()
        parsed_content = parsing_service.parse_document(
            file_path=temp_path, method=parsing_option, metadata=metadata
        )

        # 清理临时文件
        os.remove(temp_path)

        return parsed_content
    except Exception as e:
        logger.error(f"Error parsing file: {str(e)}")
        # 记录详细错误信息，便于调试
        import traceback

        logger.error(traceback.format_exc())

        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")


@app.post("/load")
async def load_file(
    file: UploadFile = File(...),
    loading_method: str = Form(...),
    strategy: str = Form(None),
    chunking_strategy: str = Form(None),
    chunking_options: str = Form(None),
):
    """
    加载文档文件并进行初步处理
    
    功能：上传并加载文档，支持多种加载策略和分块策略
    
    参数：
    - file: 上传的文件
    - loading_method: 加载方法
    - strategy: 加载策略（可选）
    - chunking_strategy: 分块策略（可选）
    - chunking_options: 分块选项（JSON格式，可选）
    
    返回：
    - loaded_content: 加载后的文档内容
    - filepath: 保存的文件路径
    """
    try:
        # 保存上传的文件
        temp_path = os.path.join("temp", file.filename)
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 准备元数据
        metadata = {
            "filename": file.filename,
            "total_chunks": 0,  # 将在后面更新
            "total_pages": 0,  # 将在后面更新
            "loading_method": loading_method,
            "loading_strategy": strategy,
            "chunking_strategy": chunking_strategy,
            "timestamp": datetime.now().isoformat(),
        }

        # Parse chunking options if provided
        chunking_options_dict = None
        if chunking_options:
            try:
                chunking_options_dict = json.loads(chunking_options)
            except json.JSONDecodeError:
                logger.warning(f"无法解析chunking_options: {chunking_options}")
                chunking_options_dict = {}
        else:
            chunking_options_dict = {}

        # 使用 LoadingService 加载文档
        loading_service = LoadingService()
        raw_text = loading_service.load_pdf(
            temp_path,
            loading_method,
            strategy=strategy,
            chunking_strategy=chunking_strategy,
            chunking_options=chunking_options_dict,
        )

        metadata["total_pages"] = loading_service.get_total_pages()

        page_map = loading_service.get_page_map()

        # 转换成标准化的chunks格式
        chunks = []
        for idx, page in enumerate(page_map, 1):
            chunk_metadata = {
                "chunk_id": idx,
                "page_number": page["page"],
                "page_range": str(page["page"]),
                "word_count": len(page["text"].split()),
            }
            if "metadata" in page:
                chunk_metadata.update(page["metadata"])

            chunks.append({"content": page["text"], "metadata": chunk_metadata})

        # 使用 LoadingService 保存文档，传递strategy参数
        filepath = loading_service.save_document(
            filename=file.filename,
            chunks=chunks,
            metadata=metadata,
            loading_method=loading_method,
            strategy=strategy,
            chunking_strategy=chunking_strategy,
        )

        # 读取保存的文档以返回
        with open(filepath, "r", encoding="utf-8") as f:
            document_data = json.load(f)

        # 清理临时文件
        os.remove(temp_path)

        return {"loaded_content": document_data, "filepath": filepath}
    except Exception as e:
        logger.error(f"Error loading file: {str(e)}")
        raise


@app.post("/chunk")
async def chunk_document(data: dict = Body(...)):
    """
    对已加载的文档进行分块处理
    
    功能：将loaded或parsed文档按指定策略进行分块
    
    参数：
    - doc_id: 文档ID
    - chunking_option: 分块方法
    - chunk_size: 分块大小（默认1000）
    - overlap_size: 重叠大小（默认50）
    
    返回：
    - loaded_content: 分块后的文档内容
    - filepath: 保存的文件路径
    - output_file: 输出文件名
    - chunked_doc_id: 分块文档ID
    """
    try:
        doc_id = data.get("doc_id")
        chunking_option = data.get("chunking_option")
        chunk_size = data.get("chunk_size", 1000)
        overlap_size = data.get("overlap_size", 50)

        if not doc_id or not chunking_option:
            raise HTTPException(
                status_code=400,
                detail="Missing required parameters: doc_id and chunking_option",
            )

        # 首先尝试从01-loaded-docs读取文档
        loaded_file_path = os.path.join("01-loaded-docs", doc_id)
        parsed_file_path = os.path.join("01-parsed-docs", doc_id)

        doc_data = None
        page_map = []
        metadata = {}

        if os.path.exists(loaded_file_path):
            # 从loaded文档读取（原有逻辑）
            with open(loaded_file_path, "r", encoding="utf-8") as f:
                doc_data = json.load(f)

            # 构建页面映射
            page_map = [
                {"page": chunk["metadata"]["page_number"], "text": chunk["content"]}
                for chunk in doc_data["chunks"]
            ]

            # 准备元数据
            metadata = {
                "filename": doc_data["filename"],
                "loading_method": doc_data["loading_method"],
                "total_pages": doc_data["total_pages"],
            }

        elif os.path.exists(parsed_file_path):
            # 从parsed文档读取（使用新的JSON分块方法）
            with open(parsed_file_path, "r", encoding="utf-8") as f:
                doc_data = json.load(f)

            # 使用新的chunk_parsed_json方法，只处理markdown内容
            chunking_service = ChunkingService()
            result = chunking_service.chunk_parsed_json(
                parsed_data=doc_data,
                method=chunking_option,
                chunk_size=chunk_size,
                overlap_size=overlap_size,
            )

        else:
            raise HTTPException(
                status_code=404,
                detail="Document not found in loaded or parsed directories",
            )

        # 对于loaded文档，使用旧的chunk_text方法
        if os.path.exists(loaded_file_path):
            # 检查是否有有效的页面映射
            if not page_map:
                raise HTTPException(
                    status_code=400, detail="No valid content found for chunking"
                )

            chunking_service = ChunkingService()
            result = chunking_service.chunk_text(
                text="",  # 不需要传递文本，因为我们使用 page_map
                method=chunking_option,
                metadata=metadata,
                page_map=page_map,
                chunk_size=chunk_size,
                overlap_size=overlap_size,
            )

        # 修复输出文件名以匹配前端期望的格式
        # 使用原始doc_id而不是从metadata获取的filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base_name = doc_id.replace(".json", "")
        expected_output_file = f"{base_name}_{chunking_option}_{timestamp}.json"

        # 更新result中的filename和output_file以匹配前端期望
        result["filename"] = doc_id
        result["output_file"] = expected_output_file

        # 使用chunking_service的save_document方法保存结果
        filepath = chunking_service.save_document(document_data=result)

        # 读取保存的文档以返回
        with open(filepath, "r", encoding="utf-8") as f:
            document_data = json.load(f)

        return {
            "loaded_content": document_data,
            "filepath": filepath,
            "output_file": expected_output_file,
            "chunked_doc_id": expected_output_file,
        }
    except Exception as e:
        logger.error(f"Error chunking document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate")
async def evaluate_search(
    file: UploadFile = File(...),
    collection_id: str = Form(...),
    top_k: int = Form(10),
    threshold: float = Form(0.7),
):
    """
    评估搜索效果
    
    功能：使用CSV文件中的查询和标签评估搜索系统的准确性
    
    参数：
    - file: 包含查询和标签的CSV文件
    - collection_id: 要搜索的集合ID
    - top_k: 每个查询返回的结果数量（默认10）
    - threshold: 相似度阈值（默认0.7）
    
    返回：
    - results: 每个查询的详细评估结果
    - average_scores: 平均分数（score_hit和score_find）
    - total_queries: 有效查询总数
    - parameters: 评估参数
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(file.file)

        # 只合并前四列的文本内容
        df["combined_text"] = df.apply(
            lambda row: " ".join(
                str(val)
                for i, val in enumerate(row)
                if i < 4 and pd.notna(val) and val != "[]"
            ),
            axis=1,
        )

        # 初始化SearchService
        search_service = SearchService()

        results = []
        total_score_hit = 0
        total_score_find = 0
        valid_queries = 0

        # 处理每个查询
        for _, row in df.iterrows():
            # 跳过没有标签的行
            if pd.isna(row["LABEL"]) or row["LABEL"] == "[]":
                continue

            try:
                # 解析标签页码列表
                label_str = str(row["LABEL"]).strip("[]").replace(" ", "")
                if label_str:
                    expected_pages = [
                        int(x.strip()) for x in label_str.split(",") if x.strip()
                    ]
                else:
                    continue

                # 执行搜索
                search_results = await search_service.search(
                    query=row["combined_text"],
                    collection_id=collection_id,
                    top_k=top_k,
                    threshold=threshold,
                )

                # 提取找到的页码
                found_pages = [
                    int(result["metadata"]["page"]) for result in search_results
                ]

                # 计算分数
                hits = sum(1 for page in found_pages if page in expected_pages)
                score_hit = hits / len(found_pages) if found_pages else 0
                score_find = len(set(found_pages) & set(expected_pages)) / len(
                    expected_pages
                )

                # 添加到结果列表，包括所有top_k结果的文本
                result_entry = {
                    "query": row["combined_text"],
                    "expected_pages": expected_pages,
                    "found_pages": found_pages,
                    "score_hit": score_hit,
                    "score_find": score_find,
                }

                # 添加每个top_k结果的文本作为单独的字段
                for i, result in enumerate(search_results, 1):
                    result_entry[f"text_{i}"] = result["text"]
                    result_entry[f"page_{i}"] = result["metadata"]["page"]
                    result_entry[f"score_{i}"] = result["score"]

                results.append(result_entry)

                total_score_hit += score_hit
                total_score_find += score_find
                valid_queries += 1

            except Exception as e:
                logger.warning(f"Error processing row: {str(e)}")
                continue

        if valid_queries == 0:
            raise ValueError("No valid queries found in the CSV file")

        # 计算平均分数
        average_scores = {
            "score_hit": total_score_hit / valid_queries,
            "score_find": total_score_find / valid_queries,
        }

        # 保存结果
        output_dir = Path("06-evaluation-result")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细的JSON结果
        output_path = output_dir / f"evaluation_results_{timestamp}.json"
        evaluation_results = {
            "results": results,
            "average_scores": average_scores,
            "total_queries": valid_queries,
            "parameters": {
                "collection_id": collection_id,
                "top_k": top_k,
                "threshold": threshold,
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_results, f, indent=2)

        # 保存CSV格式的结果，每个top_k结果单独一列
        results_df = pd.DataFrame(results)

        # 重新排列列的顺序，使其更有逻辑性
        column_order = [
            "query",
            "expected_pages",
            "found_pages",
            "score_hit",
            "score_find",
        ]
        for i in range(1, top_k + 1):
            column_order.extend([f"page_{i}", f"score_{i}", f"text_{i}"])

        # 只选择存在的列
        existing_columns = [col for col in column_order if col in results_df.columns]
        results_df = results_df[existing_columns]

        csv_path = output_dir / f"evaluation_results_{timestamp}.csv"
        results_df.to_csv(csv_path, index=False)

        return evaluation_results

    except Exception as e:
        logger.error(f"Error during evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save-search")
async def save_search_results(request: Request):
    """
    保存搜索结果
    
    功能：将搜索结果保存到04-search-results目录
    
    参数：
    - query: 搜索查询
    - collection_id: 集合ID
    - results: 搜索结果列表
    
    返回：
    - saved_filepath: 保存的文件路径
    """
    try:
        data = await request.json()
        query = data.get("query")
        collection_id = data.get("collection_id")
        results = data.get("results")

        if not all([query, collection_id, results]):
            raise HTTPException(status_code=400, detail="Missing required parameters")

        # 直接创建 SearchService 实例
        search_service = SearchService()
        filepath = search_service.save_search_results(query, collection_id, results)
        return {"saved_filepath": filepath}

    except Exception as e:
        logger.error(f"Error saving search results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generation/models")
async def get_generation_models():
    """
    获取可用的文本生成模型列表
    
    功能：返回系统支持的所有文本生成模型
    
    返回：
    - models: 可用的生成模型列表
    """
    try:
        generation_service = GenerationService()
        models = generation_service.get_available_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error getting generation models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate_response(
    query: str = Body(...),
    provider: str = Body(...),
    model_name: str = Body(...),
    search_results: List[Dict] = Body(...),
    api_key: Optional[str] = Body(None),
):
    """
    基于搜索结果生成回答
    
    功能：使用指定的生成模型，基于搜索结果生成相关回答
    
    参数：
    - query: 用户查询
    - provider: 生成服务提供商
    - model_name: 生成模型名称
    - search_results: 搜索结果列表
    - api_key: API密钥（可选）
    
    返回：
    - 生成的回答内容
    """
    try:
        generation_service = GenerationService()
        result = generation_service.generate(
            provider=provider,
            model_name=model_name,
            query=query,
            search_results=search_results,
            api_key=api_key,
        )
        return result
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search-results")
async def list_search_results():
    """
    获取所有搜索结果文件列表
    
    功能：列出04-search-results目录中的所有搜索结果文件
    
    返回：
    - files: 搜索结果文件列表，包含ID、名称和时间戳
    """
    try:
        search_results_dir = "04-search-results"
        if not os.path.exists(search_results_dir):
            return {"files": []}

        files = []
        for filename in os.listdir(search_results_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(search_results_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    files.append(
                        {
                            "id": filename,
                            "name": f"Search: {data.get('query', 'Unknown')} ({filename})",
                            "timestamp": data.get("timestamp", ""),
                        }
                    )

        # 按时间戳排序，最新的在前面
        files.sort(key=lambda x: x["timestamp"], reverse=True)
        return {"files": files}

    except Exception as e:
        logger.error(f"Error listing search results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search-results/{file_id}")
async def get_search_result(file_id: str):
    """
    获取特定搜索结果文件的内容
    
    功能：读取并返回指定搜索结果文件的完整内容
    
    参数：
    - file_id: 搜索结果文件ID
    
    返回：
    - 搜索结果文件的完整内容
    """
    try:
        file_path = os.path.join("04-search-results", file_id)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Search result file not found")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data

    except Exception as e:
        logger.error(f"Error reading search result file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/{provider}")
async def search_with_path_param(provider: str, body: dict = Body(...)):
    """
    执行向量相似性搜索（通过路径参数）
    
    功能：在指定提供商的向量数据库中执行相似性搜索
    
    参数（路径）：
    - provider: 向量数据库提供商名称
    
    参数（请求体）：
    - query: 搜索查询文本
    - collection_id: 集合ID
    - top_k: 返回结果数量（默认3）
    - threshold: 相似度阈值（默认0.5）
    - word_count_threshold: 最小字数阈值（默认30）
    - save_results: 是否保存搜索结果（默认false）
    
    返回：
    - results: 搜索结果列表，包含文本内容、元数据和相似度分数
    """
    try:
        # 从请求体中提取参数
        query = body.get("query", "")
        collection_id = body.get("collection_id", "")
        top_k = body.get("top_k", 3)
        threshold = body.get("threshold", 0.5)  # 相似度阈值默认50%
        word_count_threshold = body.get("word_count_threshold", 30)  # 最小字数默认30
        save_results = body.get("save_results", False)

        # Log the incoming search request details
        logger.info(
            f"Search request with path param - Raw Provider: {provider}, Query: {query}, Collection: {collection_id}, Top K: {top_k}, Threshold: {threshold}, Word Count Threshold: {word_count_threshold}"
        )

        # 验证集合ID是否为字符串
        if not isinstance(collection_id, str):
            collection_id = str(collection_id)
            logger.warning(f"Converted collection_id to string: {collection_id}")

        # 确保 provider 是字符串
        if not isinstance(provider, str):
            provider = str(provider)

        # 规范化 provider 字符串 (确保为小写)
        provider_str = provider.lower().strip()

        # 验证 provider_str 是否为有效值
        if provider_str not in [
            VectorDBProvider.MILVUS.value,
            VectorDBProvider.CHROMA.value,
        ]:
            logger.warning(f"Invalid provider: {provider_str}, defaulting to milvus")
            provider_str = VectorDBProvider.MILVUS.value

        logger.info(f"Using provider: '{provider_str}'")

        search_service = SearchService()

        # Log before calling the search function
        logger.info("Calling search service...")

        results = await search_service.search(
            provider=provider_str,
            query=query,
            collection_id=collection_id,
            top_k=top_k,
            threshold=threshold,
            word_count_threshold=word_count_threshold,
            save_results=save_results,
        )

        # Log the search results
        logger.info(f"Search response: {results}")

        return {"results": results}
    except Exception as e:
        logger.error(f"Error performing search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    系统健康检查
    
    功能：检查系统运行状态
    
    返回：
    - status: 系统状态（healthy）
    - timestamp: 检查时间戳
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    logger.info("=== Starting RAG Framework Backend ===")
    logger.info("Server will start on http://0.0.0.0:8003")

    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True, log_level="info")
