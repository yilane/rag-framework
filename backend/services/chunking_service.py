from datetime import datetime
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from llama_index.core.node_parser import (
    SentenceSplitter,
    SemanticSplitterNodeParser,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logger = logging.getLogger(__name__)

class ChunkingService:
    """
    文本分块服务，提供多种文本分块策略
    
    该服务支持以下分块方法：
    - by_pages: 按页面分块，每页作为一个块
    - fixed_size: 按固定大小分块
    - by_paragraphs: 按段落分块
    - by_sentences: 按句子分块
    """
    
    def chunk_text(self, text: str, method: str, metadata: dict, page_map: list = None, chunk_size: int = 1000, overlap_size: int = 50) -> dict:
        """
        将文本按指定方法分块
        
        Args:
            text: 原始文本内容
            method: 分块方法，支持 'by_pages', 'fixed_size', 'by_paragraphs', 'by_sentences', 'by_semantic'
            metadata: 文档元数据
            page_map: 页面映射列表，每个元素包含页码和页面文本
            chunk_size: 固定大小分块时的块大小
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
                        "page_number": page_data['page'],
                        "page_range": str(page_data['page']),
                        "word_count": len(page_data['text'].split())
                    }
                    chunks.append({
                        "content": page_data['text'],
                        "metadata": chunk_metadata
                    })
            
            elif method == "fixed_size":
                # 对每页内容进行固定大小分块
                for page_data in page_map:
                    page_chunks = self._fixed_size_chunks(page_data['text'], chunk_size, overlap_size)
                    for idx, chunk in enumerate(page_chunks, 1):
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "page_number": page_data['page'],
                            "page_range": str(page_data['page']),
                            "word_count": len(chunk["text"].split())
                        }
                        chunks.append({
                            "content": chunk["text"],
                            "metadata": chunk_metadata
                        })
            
            elif method in ["by_paragraphs", "by_sentences"]:
                # 对每页内容进行段落或句子分块
                splitter_method = self._paragraph_chunks if method == "by_paragraphs" else self._sentence_chunks
                for page_data in page_map:
                    page_chunks = splitter_method(page_data['text'])
                    for chunk in page_chunks:
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "page_number": page_data['page'],
                            "page_range": str(page_data['page']),
                            "word_count": len(chunk["text"].split())
                        }
                        chunks.append({
                            "content": chunk["text"],
                            "metadata": chunk_metadata
                        })
            elif method == "by_semantic":
                # 按语义分块
                for page_data in page_map:
                    # 对每页内容进行语义分块
                    page_chunks = self._semantic_chunks(page_data['text'], chunk_size, overlap_size)
                    for chunk in page_chunks:
                        chunk_metadata = {
                            "chunk_id": len(chunks) + 1,
                            "page_number": page_data['page'],
                            "page_range": str(page_data['page']),
                            "word_count": len(chunk["text"].split())
                        }
                        chunks.append({
                            "content": chunk["text"],
                            "metadata": chunk_metadata
                        })
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
                "chunks": chunks
            }
            
            return document_data
            
        except Exception as e:
            logger.error(f"Error in chunk_text: {str(e)}")
            raise

    def _fixed_size_chunks(self, text: str, chunk_size: int, overlap_size: int) -> list[dict]:
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
        
        Args:
            text: 要分块的文本
            
        Returns:
            分块后的段落列表
        """
        # 使用递归分割器，但只使用段落分隔符，确保仅在段落边界处分割
        text_splitter = RecursiveCharacterTextSplitter(
            # 只使用段落相关的分隔符，这样确保只在段落处分割
            separators=["\n\n", "\n\r\n", "\r\n\r\n", "\n\n\n"],
            # 设置较大的块大小，确保段落通常不会被进一步分割
            chunk_size=2000,
            chunk_overlap=0,  # 段落间通常不需要重叠
            length_function=len,
        )
        
        # 分割文本
        paragraphs = text_splitter.split_text(text)
        
        # 过滤掉空段落，并转换为所需的输出格式
        return [{"text": para} for para in paragraphs if para.strip()]

    def _sentence_chunks(self, text: str) -> list[dict]:
        """
        将文本按句子分块
        
        Args:
            text: 要分块的文本
            
        Returns:
            分块后的句子列表
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        )
        texts = splitter.split_text(text)
        return [{"text": t} for t in texts]

    def _semantic_chunks(self, text: str, chunk_size: int = 1000, overlap_size: int = 50) -> list[dict]:
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
                chunk_size=chunk_size,
                chunk_overlap=overlap_size
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
                embed_model=embed_model  # 使用HuggingFace嵌入模型
            )
            
            # 分割文本
            nodes = semantic_splitter.get_nodes_from_documents(
                [text]
            )
            
            # 从节点中提取文本并转换为所需的输出格式
            return [{"text": node.text} for node in nodes if node.text.strip()]
        except Exception as e:
            logger.error(f"Error in semantic chunking: {str(e)}")
            # 如果语义分块失败，返回固定大小分块作为备选
            logger.warning("Falling back to fixed size chunking")
            return self._fixed_size_chunks(text, chunk_size, overlap_size)
