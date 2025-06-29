from datetime import datetime
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_index.core.node_parser import (
    SentenceSplitter,
    SemanticSplitterNodeParser,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os
import json

logger = logging.getLogger(__name__)


class ChunkingService:
    """
    文本分块服务，提供多种文本分块策略

    该服务支持以下分块方法：
    - by_pages: 按页面分块，每页作为一个块
    - fixed_size: 按固定大小分块
    - by_paragraphs: 按段落分块（针对markdown优化）
    - by_sentences: 按句子分块（针对markdown优化）
    - markdown_aware: markdown语法感知的智能分块（新增）
    - by_semantic: 按语义相关性分块

    支持两种输入格式：
    - 传统的text + page_map格式（使用chunk_text方法）
    - JSON格式的解析结果（使用chunk_parsed_json方法，只处理type为'markdown'的内容）
    """

    def chunk_text(
        self,
        text: str,
        method: str,
        metadata: dict,
        page_map: list = None,
        chunk_size: int = 500,
        overlap_size: int = 50,
    ) -> dict:
        """
        将文本按指定方法分块

        Args:
            text: 原始文本内容
            method: 分块方法，支持 'by_pages', 'fixed_size', 'by_paragraphs', 'by_sentences', 'markdown_aware', 'by_semantic'
            metadata: 文档元数据
            page_map: 页面映射列表，每个元素包含页码和页面文本
            chunk_size: 固定大小分块时的块大小，markdown_aware时的目标块大小
            overlap_size: 固定大小分块时的重叠大小，即相邻块之间共享的字符数
        Returns:
            包含分块结果的文档数据结构

        Raises:
            ValueError: 当分块方法不支持或页面映射为空时
        """
        try:
            if not page_map:
                raise ValueError("Page map is required for chunking.")

            chunks = []
            total_pages = len(page_map)

            if method == "by_pages":
                # 直接使用 page_map 中的每页作为一个 chunk
                for page_data in page_map:
                    chunk_metadata = {
                        "chunk_id": len(chunks) + 1,
                        "page_number": page_data["page"],
                        "page_range": str(page_data["page"]),
                        "word_count": len(page_data["text"].split()),
                    }
                    chunks.append(
                        {"content": page_data["text"], "metadata": chunk_metadata}
                    )

            elif method == "fixed_size":
                # 对每页内容进行固定大小分块
                for page_data in page_map:
                    page_chunks = self._fixed_size_chunks(
                        page_data["text"], chunk_size, overlap_size
                    )
                    for idx, chunk in enumerate(page_chunks, 1):
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "page_number": page_data["page"],
                            "page_range": str(page_data["page"]),
                            "word_count": len(chunk["text"].split()),
                        }
                        chunks.append(
                            {"content": chunk["text"], "metadata": chunk_metadata}
                        )

            elif method in ["by_paragraphs", "by_sentences", "markdown_aware"]:
                # 对每页内容进行段落、句子或markdown智能分块
                if method == "by_paragraphs":
                    splitter_method = self._paragraph_chunks
                elif method == "by_sentences":
                    splitter_method = self._sentence_chunks
                else:  # markdown_aware
                    splitter_method = self._markdown_aware_chunks
                    
                for page_data in page_map:
                    if method == "markdown_aware":
                        page_chunks = splitter_method(page_data["text"], chunk_size)
                    else:
                        page_chunks = splitter_method(page_data["text"])
                    for chunk in page_chunks:
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "page_number": page_data["page"],
                            "page_range": str(page_data["page"]),
                            "word_count": len(chunk["text"].split()),
                        }
                        chunks.append(
                            {"content": chunk["text"], "metadata": chunk_metadata}
                        )
            elif method == "by_semantic":
                # 按语义分块
                for page_data in page_map:
                    # 对每页内容进行语义分块
                    page_chunks = self._semantic_chunks(
                        page_data["text"], chunk_size, overlap_size
                    )
                    for chunk in page_chunks:
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "page_number": page_data["page"],
                            "page_range": str(page_data["page"]),
                            "word_count": len(chunk["text"].split()),
                        }
                        chunks.append(
                            {"content": chunk["text"], "metadata": chunk_metadata}
                        )
            else:
                raise ValueError(f"Unsupported chunking method: {method}")

            # 创建标准化的文档数据结构
            document_data = {
                "filename": metadata.get("filename", ""),
                "total_chunks": len(chunks),
                "total_pages": total_pages,
                "loading_method": metadata.get("loading_method", ""),
                "chunking_method": method,
                "timestamp": datetime.now().isoformat(),
                "chunks": chunks,
            }

            return document_data

        except Exception as e:
            logger.error(f"Error in chunk_text: {str(e)}")
            raise

    def chunk_parsed_json(
        self,
        parsed_data: dict,
        method: str,
        chunk_size: int = 500,
        overlap_size: int = 50,
    ) -> dict:
        """
        对JSON格式的解析结果进行分块，只处理type为'markdown'的内容

        Args:
            parsed_data: JSON格式的解析结果，包含metadata和content字段
            method: 分块方法，支持 'by_content', 'fixed_size', 'by_paragraphs', 'by_sentences', 'markdown_aware', 'by_semantic'
            chunk_size: 固定大小分块时的块大小，markdown_aware时的目标块大小
            overlap_size: 固定大小分块时的重叠大小
        Returns:
            包含分块结果的文档数据结构

        Raises:
            ValueError: 当输入数据格式不正确或分块方法不支持时
        """
        try:
            # 验证输入数据格式
            if not isinstance(parsed_data, dict):
                raise ValueError("parsed_data must be a dictionary")

            if "content" not in parsed_data:
                raise ValueError("parsed_data must contain 'content' field")

            metadata = parsed_data.get("metadata", {})
            content_items = parsed_data.get("content", [])

            # 过滤出type为'markdown'的内容项
            markdown_items = [
                item for item in content_items if item.get("type") == "markdown"
            ]

            if not markdown_items:
                logger.warning("No markdown content found in parsed data")
                # 返回空的文档数据结构
                return {
                    "filename": metadata.get("filename", ""),
                    "total_chunks": 0,
                    "total_pages": metadata.get("total_pages", 0),
                    "loading_method": metadata.get("parsing_method", "marker"),
                    "chunking_method": method,
                    "timestamp": datetime.now().isoformat(),
                    "chunks": [],
                }

            chunks = []

            if method == "by_content":
                # 直接使用每个markdown内容项作为一个chunk
                for idx, item in enumerate(markdown_items, 1):
                    content = item.get("content", "")
                    # 获取页面信息，如果没有则使用默认值
                    page_num = item.get("page", 1)
                    chunk_metadata = {
                        "chunk_id": idx,
                        "source_item_index": content_items.index(
                            item
                        ),  # 在原始内容中的索引
                        "page_number": page_num,  # 添加页面编号
                        "page_range": str(page_num),  # 添加页面范围
                        "word_count": len(content.split()),
                        "confidence": item.get("confidence"),  # 保留置信度信息
                    }
                    chunks.append({"content": content, "metadata": chunk_metadata})

            elif method == "fixed_size":
                # 对每个markdown内容项进行固定大小分块
                for item in markdown_items:
                    content = item.get("content", "")
                    if not content.strip():
                        continue

                    page_num = item.get("page", 1)  # 获取页面信息
                    content_chunks = self._fixed_size_chunks(
                        content, chunk_size, overlap_size
                    )
                    for chunk in content_chunks:
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "source_item_index": content_items.index(item),
                            "page_number": page_num,  # 添加页面编号
                            "page_range": str(page_num),  # 添加页面范围
                            "word_count": len(chunk["text"].split()),
                            "confidence": item.get("confidence"),
                        }
                        chunks.append(
                            {"content": chunk["text"], "metadata": chunk_metadata}
                        )

            elif method in ["by_paragraphs", "by_sentences", "markdown_aware"]:
                # 对每个markdown内容项进行段落、句子或markdown智能分块
                if method == "by_paragraphs":
                    splitter_method = self._paragraph_chunks
                elif method == "by_sentences":
                    splitter_method = self._sentence_chunks
                else:  # markdown_aware
                    splitter_method = self._markdown_aware_chunks
                    
                for item in markdown_items:
                    content = item.get("content", "")
                    if not content.strip():
                        continue

                    page_num = item.get("page", 1)  # 获取页面信息
                    if method == "markdown_aware":
                        content_chunks = splitter_method(content, chunk_size)
                    else:
                        content_chunks = splitter_method(content)
                    for chunk in content_chunks:
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "source_item_index": content_items.index(item),
                            "page_number": page_num,  # 添加页面编号
                            "page_range": str(page_num),  # 添加页面范围
                            "word_count": len(chunk["text"].split()),
                            "confidence": item.get("confidence"),
                        }
                        chunks.append(
                            {"content": chunk["text"], "metadata": chunk_metadata}
                        )

            elif method == "by_semantic":
                # 按语义分块
                for item in markdown_items:
                    content = item.get("content", "")
                    if not content.strip():
                        continue

                    page_num = item.get("page", 1)  # 获取页面信息
                    content_chunks = self._semantic_chunks(
                        content, chunk_size, overlap_size
                    )
                    for chunk in content_chunks:
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "source_item_index": content_items.index(item),
                            "page_number": page_num,  # 添加页面编号
                            "page_range": str(page_num),  # 添加页面范围
                            "word_count": len(chunk["text"].split()),
                            "confidence": item.get("confidence"),
                        }
                        chunks.append(
                            {"content": chunk["text"], "metadata": chunk_metadata}
                        )
            else:
                raise ValueError(f"Unsupported chunking method: {method}")

            # 创建标准化的文档数据结构
            document_data = {
                "filename": metadata.get("filename", ""),
                "total_chunks": len(chunks),
                "total_pages": metadata.get("total_pages", 0),
                "total_markdown_items": len(markdown_items),
                "total_content_items": len(content_items),
                "loading_method": metadata.get("parsing_method", "marker"),
                "chunking_method": method,
                "timestamp": datetime.now().isoformat(),
                "chunks": chunks,
            }

            logger.info(
                f"Successfully chunked {len(markdown_items)} markdown items into {len(chunks)} chunks using method '{method}'"
            )
            return document_data

        except Exception as e:
            logger.error(f"Error in chunk_parsed_json: {str(e)}")
            raise

    def _fixed_size_chunks(
        self, text: str, chunk_size: int = 500, overlap_size: int = 50
    ) -> list[dict]:
        """
        将文本按固定大小分块，使用RecursiveCharacterTextSplitter实现

        Args:
            text: 要分块的文本
            chunk_size: 每块的最大字符数
            overlap_size: 相邻块之间的重叠字符数，用于保持上下文连贯性
        Returns:
            分块后的文本列表
        """
        # 使用递归分割器，它会尝试在句子边界分割，然后是段落边界，最后是单词边界
        text_splitter = RecursiveCharacterTextSplitter(
            # 分隔符顺序很重要，它会首先尝试在段落处分割，然后是句子，最后是单词
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            length_function=len,  # 使用默认的len函数计算长度
        )

        # 分割文本
        chunks = text_splitter.split_text(text)

        # 转换为所需的输出格式
        return [{"text": chunk} for chunk in chunks]

    def _paragraph_chunks(self, text: str) -> list[dict]:
        """
        将文本按段落分块，使用RecursiveCharacterTextSplitter实现
        针对markdown格式优化，考虑标题、列表、代码块等特殊结构

        Args:
            text: 要分块的文本

        Returns:
            分块后的段落列表
        """
        # 针对markdown格式优化的分隔符
        # 优先级从高到低：标题分隔、段落分隔、列表分隔
        markdown_separators = [
            # 标题前后的分隔（确保标题独立成块）
            "\n# ",      # 一级标题
            "\n## ",     # 二级标题  
            "\n### ",    # 三级标题
            "\n#### ",   # 四级标题
            "\n##### ", # 五级标题
            "\n###### ",# 六级标题
            
            # 代码块的分隔
            "\n```\n",   # 代码块开始/结束
            "```\n",     # 代码块结束
            
            # 段落分隔符（双换行）
            "\n\n",      # 标准段落分隔
            "\n\r\n",    # Windows格式
            "\r\n\r\n",  # Windows双换行
            "\n\n\n",    # 多个换行
            
            # 列表项分隔
            "\n- ",      # 无序列表
            "\n* ",      # 无序列表（星号）
            "\n+ ",      # 无序列表（加号）
            "\n1. ",     # 有序列表
            "\n2. ",     # 有序列表
            "\n3. ",     # 有序列表（可扩展到更多数字）
            
            # 引用和其他特殊格式
            "\n> ",      # 引用块
            "\n---\n",   # 水平分割线
            "\n***\n",   # 水平分割线
            
            # 表格分隔（表格行）
            "|\n",       # 表格行结束
        ]
        
        text_splitter = RecursiveCharacterTextSplitter(
            separators=markdown_separators,
            # 适当增加chunk_size以适应markdown结构的完整性
            chunk_size=800,  # 从500增加到800，确保markdown结构完整
            chunk_overlap=50,  # 添加适当重叠，保持上下文连贯
            length_function=len,
        )

        # 分割文本
        paragraphs = text_splitter.split_text(text)

        # 过滤掉空段落，并转换为所需的输出格式
        return [{"text": para} for para in paragraphs if para.strip()]

    def _sentence_chunks(self, text: str) -> list[dict]:
        """
        将文本按句子分块
        针对markdown格式优化，考虑链接、强调等内联语法

        Args:
            text: 要分块的文本

        Returns:
            分块后的句子列表
        """
        # 针对markdown优化的句子分隔符
        markdown_sentence_separators = [
            # 段落级分隔符（优先级最高）
            "\n\n",      # 段落分隔
            "\n# ",      # 标题（确保不会在标题中间分割）
            "\n## ",
            "\n### ",
            
            # 句子结束符（中文）
            "。\n",      # 句号+换行（优先）
            "！\n",      # 感叹号+换行
            "？\n",      # 问号+换行
            "；\n",      # 分号+换行
            
            # 句子结束符（不带换行）
            "。",        # 句号
            "！",        # 感叹号
            "？",        # 问号
            "；",        # 分号
            
            # 次要分隔符
            "，",        # 逗号
            "\n",        # 单换行
            
            # 英文句子结束符
            ". ",        # 英文句号+空格
            "! ",        # 英文感叹号+空格
            "? ",        # 英文问号+空格
            "; ",        # 英文分号+空格
            
            # 最后的备选分隔符
            " ",         # 空格
            "",          # 字符级分割（最后选择）
        ]
        
        splitter = RecursiveCharacterTextSplitter(
            # 减小chunk_size以确保真正的句子级分割
            chunk_size=200,  # 从300降低到200，更精确的句子分割
            chunk_overlap=30,  # 适当调整重叠，保持句子完整性
            separators=markdown_sentence_separators,
        )
        texts = splitter.split_text(text)
        return [{"text": t} for t in texts]

    def _semantic_chunks(
        self, text: str, chunk_size: int = 500, overlap_size: int = 50
    ) -> list[dict]:
        """
        将文本按语义相关性分块，使用SemanticSplitterNodeParser实现

        Args:
            text: 要分块的文本
            chunk_size: 每块的最大字符数
            overlap_size: 相邻块之间的重叠字符数

        Returns:
            分块后的语义块列表
        """
        try:
            # 使用llama_index的语义分割器
            # 预先使用句子分割器进行初步分割
            sentence_splitter = SentenceSplitter(
                chunk_size=chunk_size, chunk_overlap=overlap_size
            )

            # 使用HuggingFace嵌入模型
            # 这里使用multilingual模型，更适合中文处理
            embed_model = HuggingFaceEmbedding(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )

            # 使用语义分割器进行最终分割
            semantic_splitter = SemanticSplitterNodeParser(
                buffer_size=1,  # 缓冲区大小，用于合并相似的语义块
                sentence_splitter=sentence_splitter,
                embed_model=embed_model,  # 使用HuggingFace嵌入模型
            )

            # 分割文本 - 需要先创建Document对象
            from llama_index.core import Document

            doc = Document(text=text)
            nodes = semantic_splitter.get_nodes_from_documents([doc])

            # 从节点中提取文本并转换为所需的输出格式
            return [{"text": node.text} for node in nodes if node.text.strip()]
        except Exception as e:
            logger.error(f"Error in semantic chunking: {str(e)}")
            # 如果语义分块失败，返回固定大小分块作为备选
            logger.warning("Falling back to fixed size chunking")
            return self._fixed_size_chunks(text, chunk_size, overlap_size)

    def save_document(
        self,
        doc_name: str = None,
        chunks: list = None,
        document_data: dict = None,
        chunking_method: str = None,
    ) -> str:
        """
        保存分块后的文档数据到文件。

        可以通过两种方式调用:
        1. 提供document_data: 直接保存完整的文档数据
        2. 提供chunks和其他参数: 构造文档数据并保存

        参数:
            doc_name (str, optional): 文档名称，用于构建输出文件名
            chunks (list, optional): 文档分块列表
            document_data (dict, optional): 完整的文档数据对象，如果提供则直接保存
            chunking_method (str, optional): 使用的分块方法

        返回:
            str: 保存的文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs("01-chunked-docs", exist_ok=True)

            # 如果提供了document_data，直接使用
            if document_data:
                output_data = document_data
                # 确保有output_file字段
                if "output_file" not in output_data:
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    # 尝试从文档数据中提取文件名
                    base_name = (
                        output_data.get("filename", "document")
                        .replace(".pdf", "")
                        .split("_")[0]
                    )
                    output_data["output_file"] = (
                        f"{base_name}_{output_data.get('chunking_method', 'chunked')}_{timestamp}.json"
                    )
            else:
                # 验证必要的参数
                if not chunks or not doc_name or not chunking_method:
                    raise ValueError("Missing required parameters for saving document")

                # 构建文档数据
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                base_name = doc_name.replace(".pdf", "").split("_")[0]
                output_filename = f"{base_name}_{chunking_method}_{timestamp}.json"

                output_data = {
                    "filename": doc_name,
                    "total_chunks": len(chunks),
                    "total_pages": (
                        max(
                            [
                                chunk["metadata"].get("page_number", 1)
                                for chunk in chunks
                            ]
                        )
                        if chunks
                        else 1
                    ),
                    "chunking_method": chunking_method,
                    "timestamp": datetime.now().isoformat(),
                    "chunks": chunks,
                    "output_file": output_filename,
                }

            # 保存到文件
            output_path = os.path.join("01-chunked-docs", output_data["output_file"])

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Document saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving chunked document: {str(e)}")
            raise

    def _markdown_aware_chunks(self, text: str, chunk_size: int = 600) -> list[dict]:
        """
        新增：markdown语法感知的智能分块
        
        针对markdown格式的高级分块策略，确保：
        1. 标题不会被分割
        2. 代码块保持完整
        3. 列表项不会被不当分割
        4. 表格结构保持完整
        
        Args:
            text: 要分块的markdown文本
            chunk_size: 目标块大小
            
        Returns:
            分块后的内容列表
        """
        import re
        
        # 预处理：识别特殊的markdown结构
        chunks = []
        current_chunk = ""
        current_size = 0
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检查是否是标题
            if re.match(r'^#{1,6}\s+', line):
                # 如果当前chunk已有内容且接近大小限制，则保存当前chunk
                if current_chunk and current_size > chunk_size * 0.7:
                    chunks.append({"text": current_chunk.strip()})
                    current_chunk = ""
                    current_size = 0
                # 标题开始新的块
                current_chunk += line + '\n'
                current_size += len(line) + 1
                
            # 检查是否是代码块开始
            elif line.strip().startswith('```'):
                # 如果当前chunk太大，先保存
                if current_size > chunk_size * 0.8:
                    chunks.append({"text": current_chunk.strip()})
                    current_chunk = ""
                    current_size = 0
                
                # 收集整个代码块
                code_block = line + '\n'
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_block += lines[i] + '\n'
                    i += 1
                if i < len(lines):  # 添加结束的```
                    code_block += lines[i] + '\n'
                
                # 如果代码块太大，需要单独成块
                if len(code_block) > chunk_size * 0.5:
                    if current_chunk:
                        chunks.append({"text": current_chunk.strip()})
                        current_chunk = ""
                        current_size = 0
                    chunks.append({"text": code_block.strip()})
                else:
                    current_chunk += code_block
                    current_size += len(code_block)
                    
            # 检查是否是表格行
            elif '|' in line and line.count('|') >= 2:
                current_chunk += line + '\n'
                current_size += len(line) + 1
                
            # 普通文本行
            else:
                # 检查是否需要分块
                if current_size + len(line) > chunk_size and current_chunk:
                    chunks.append({"text": current_chunk.strip()})
                    current_chunk = ""
                    current_size = 0
                    
                current_chunk += line + '\n'
                current_size += len(line) + 1
            
            i += 1
        
        # 保存最后的chunk
        if current_chunk.strip():
            chunks.append({"text": current_chunk.strip()})
            
        return chunks
