import logging
import os
import tempfile
import base64
import hashlib
import io
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

# 导入图像处理库
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available. Image processing will be limited.")

# 使用marker进行PDF解析
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    from marker.config.parser import ConfigParser
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False
    logging.warning("Marker not installed. Please install with: pip install marker-pdf")

logger = logging.getLogger(__name__)

class ParsingService:
    """
    基于Marker的多格式文档解析服务类
    
    使用开源项目marker (https://github.com/datalab-to/marker) 进行高精度文档解析
    
    支持的文件格式：
    - PDF文档 (.pdf)
    - 图像文件 (.png, .jpg, .jpeg, .bmp, .tiff, .webp等)
    - Office文档 (.docx, .doc, .pptx, .ppt, .xlsx, .xls等)
    - 网页和电子书 (.html, .htm, .epub等)
    - 纯文本文件 (.txt, .md, .markdown等)
    
    特点：
    - 统一解析流程，自动根据文件类型选择最佳转换器
    - 自动布局检测和阅读顺序识别
    - 高精度表格和图像识别
    - 统一输出标准markdown格式
    - 支持多语言OCR和多种文本编码
    - 可选LLM增强功能
    - 智能文本格式化
    """

    def __init__(self, use_llm: bool = False, force_ocr: bool = False):
        """
        初始化Marker解析服务
        
        Args:
            use_llm: 是否使用LLM提升解析质量（需要设置相应API密钥）
            force_ocr: 是否强制进行OCR重新识别
        """
        if not MARKER_AVAILABLE:
            raise ImportError(
                "Marker library not found. Please install with: pip install marker-pdf"
            )
        
        self.use_llm = use_llm
        self.force_ocr = force_ocr
        
        # 初始化marker配置
        self.config = {
            "output_format": "markdown",
            "extract_images": True,
            "force_ocr": force_ocr,
            "use_llm": use_llm,
            "save_images": False,  # 是否保存图像文件
            "include_base64": False  # 是否包含base64编码
        }
        
        # 创建保存目录
        os.makedirs("01-parsed-docs", exist_ok=True)
        
        # 初始化converter（延迟初始化以避免启动时的GPU资源占用）
        self._converter = None
        
        logger.info(f"ParsingService initialized with marker (use_llm: {use_llm}, force_ocr: {force_ocr})")
        
        # 创建图像保存目录
        self.images_dir = os.path.join("01-parsed-docs", "images")
        os.makedirs(self.images_dir, exist_ok=True)

    def _process_image(self, image_name: str, image_data: Any, save_images: bool = True, 
                       include_base64: bool = True) -> Dict[str, Any]:
        """
        处理单个图像，支持base64编码和文件保存
        
        Args:
            image_name: 图像名称
            image_data: 图像数据（可能是PIL Image、bytes或其他格式）
            save_images: 是否保存图像文件
            include_base64: 是否包含base64编码
            
        Returns:
            包含图像信息的字典
        """
        image_info = {
            "image_name": image_name,
            "format": None,
            "size": None,
            "file_path": None,
            "base64": None,
            "width": None,
            "height": None
        }
        
        try:
            # 处理不同类型的图像数据
            if PIL_AVAILABLE and hasattr(image_data, 'save'):
                # PIL Image对象
                pil_image = image_data
                image_info["format"] = pil_image.format or 'PNG'
                image_info["width"], image_info["height"] = pil_image.size
                image_info["size"] = image_info["width"] * image_info["height"]
                
                # 转换为字节数据
                img_buffer = io.BytesIO()
                save_format = image_info["format"]
                if save_format not in ['PNG', 'JPEG', 'JPG', 'BMP', 'TIFF']:
                    save_format = 'PNG'
                pil_image.save(img_buffer, format=save_format)
                image_bytes = img_buffer.getvalue()
                
            elif isinstance(image_data, (bytes, bytearray)):
                # 字节数据
                image_bytes = bytes(image_data)
                image_info["size"] = len(image_bytes)
                
                # 尝试用PIL打开以获取更多信息
                if PIL_AVAILABLE:
                    try:
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        image_info["format"] = pil_image.format
                        image_info["width"], image_info["height"] = pil_image.size
                    except Exception:
                        image_info["format"] = "unknown"
                        
            else:
                # 其他格式，尝试转换
                logger.warning(f"Unknown image format for {image_name}: {type(image_data)}")
                return image_info
            
            # 生成文件名和哈希
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_hash = hashlib.md5(image_bytes).hexdigest()[:8]
            base_name = os.path.splitext(image_name)[0]
            file_extension = f".{image_info['format'].lower()}" if image_info['format'] else ".png"
            safe_filename = f"{base_name}_{timestamp}_{file_hash}{file_extension}"
            
            # 保存图像文件
            if save_images:
                image_file_path = os.path.join(self.images_dir, safe_filename)
                with open(image_file_path, 'wb') as f:
                    f.write(image_bytes)
                image_info["file_path"] = os.path.relpath(image_file_path)
                logger.info(f"Image saved to: {image_info['file_path']}")
            
            # 生成base64编码
            if include_base64:
                base64_str = base64.b64encode(image_bytes).decode('utf-8')
                mime_type = f"image/{image_info['format'].lower()}" if image_info['format'] else "image/png"
                image_info["base64"] = f"data:{mime_type};base64,{base64_str}"
                image_info["base64_size"] = len(base64_str)
            
        except Exception as e:
            logger.error(f"Error processing image {image_name}: {str(e)}")
            image_info["error"] = str(e)
        
        return image_info

    def _replace_image_paths_in_markdown(self, markdown_text: str, processed_images: List[Dict]) -> str:
        """
        在markdown文本中替换图像路径为实际保存的路径
        
        Args:
            markdown_text: 原始markdown文本
            processed_images: 处理后的图像信息列表
            
        Returns:
            替换后的markdown文本
        """
        import re
        
        updated_markdown = markdown_text
        replacement_count = 0
        
        try:
            # 为每个处理的图像创建替换映射
            for image_info in processed_images:
                original_name = image_info.get('image_name', '')
                file_path = image_info.get('file_path', '')
                base64_data = image_info.get('base64', '')
                
                if not original_name:
                    continue
                
                # 构建新的图像引用，优先使用base64（便于前端渲染）
                if base64_data and self.config.get("include_base64", True):
                    # 优先使用base64数据，前端能直接渲染
                    new_image_ref = f"![{original_name}]({base64_data})"
                    logger.info(f"Using base64 data for image: {original_name}")
                elif file_path and self.config.get("save_images", True):
                    # 备选方案：使用保存的文件路径
                    new_image_ref = f"![{original_name}]({file_path})"
                    logger.info(f"Using file path for image: {original_name}")
                else:
                    # 保持原引用不变
                    logger.warning(f"No valid image reference found for: {original_name}")
                    continue
                
                # 查找并替换图像引用的多种可能格式
                patterns = [
                    # 标准格式: ![](image_name)
                    rf'!\[\]\({re.escape(original_name)}\)',
                    # 带文本格式: ![text](image_name)  
                    rf'!\[[^\]]*\]\({re.escape(original_name)}\)',
                    # 仅文件名（不带扩展名）
                    rf'!\[\]\({re.escape(os.path.splitext(original_name)[0])}\)',
                    rf'!\[[^\]]*\]\({re.escape(os.path.splitext(original_name)[0])}\)',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, updated_markdown)
                    if matches:
                        logger.info(f"Found {len(matches)} matches for pattern: {pattern}")
                        updated_markdown = re.sub(pattern, new_image_ref, updated_markdown)
                        replacement_count += len(matches)
                        break
                
            logger.info(f"Replaced {replacement_count} image references in markdown")
            
        except Exception as e:
            logger.error(f"Error replacing image paths in markdown: {str(e)}")
            # 返回原始markdown以防错误
            return markdown_text
        
        return updated_markdown

    def _get_converter(self, file_type: str = "pdf", file_extension: str = ".pdf"):
        """
        获取或创建合适的Converter实例（延迟初始化）
        
        Args:
            file_type: 文件类型 ('pdf', 'image', 'document')
            file_extension: 文件扩展名
        """
        # 根据文件类型创建缓存键
        converter_key = f"{file_type}_{file_extension}"
        
        # 为不同类型维护不同的converter实例
        if not hasattr(self, '_converters'):
            self._converters = {}
            
        if converter_key not in self._converters:
            try:
                # 创建配置解析器
                config_parser = ConfigParser(self.config)
                
                # 创建模型字典
                artifact_dict = create_model_dict()
                
                # 根据文件类型选择合适的转换器
                if file_type == "image":
                    # 对于图像文件，使用OCRConverter或PdfConverter
                    # marker的PdfConverter实际上也能处理图像文件
                    try:
                        from marker.converters.ocr import OCRConverter
                        self._converters[converter_key] = OCRConverter(
                            config=config_parser.generate_config_dict(),
                            artifact_dict=artifact_dict,
                            processor_list=config_parser.get_processors(),
                            renderer=config_parser.get_renderer(),
                            llm_service=config_parser.get_llm_service() if self.use_llm else None
                        )
                        logger.info(f"Marker OCRConverter initialized for {file_extension}")
                    except ImportError:
                        # 如果OCRConverter不可用，回退到PdfConverter
                        self._converters[converter_key] = PdfConverter(
                            config=config_parser.generate_config_dict(),
                            artifact_dict=artifact_dict,
                            processor_list=config_parser.get_processors(),
                            renderer=config_parser.get_renderer(),
                            llm_service=config_parser.get_llm_service() if self.use_llm else None
                        )
                        logger.info(f"Marker PdfConverter initialized for image {file_extension}")
                        
                else:
                    # 对于PDF和其他文档类型，使用PdfConverter
                    # marker的PdfConverter支持多种文档格式
                    self._converters[converter_key] = PdfConverter(
                        config=config_parser.generate_config_dict(),
                        artifact_dict=artifact_dict,
                        processor_list=config_parser.get_processors(),
                        renderer=config_parser.get_renderer(),
                        llm_service=config_parser.get_llm_service() if self.use_llm else None
                    )
                    logger.info(f"Marker PdfConverter initialized for {file_extension}")
                
            except Exception as e:
                logger.error(f"Failed to initialize converter for {file_extension}: {str(e)}")
                raise
                
        return self._converters[converter_key]

    def parse_document(self, file_path: str, method: str = None, metadata: dict = None) -> dict:
        """
        使用Marker解析文档文件，统一输出markdown格式

        Args:
            file_path (str): 文档文件的路径
            method (str): 解析方法（为向后兼容保留，实际始终使用marker）
            metadata (dict): 文档元数据，包括文件名和其他属性

        Returns:
            dict: 解析后的文档数据，包括元数据和markdown内容

        Raises:
            ValueError: 当文件不存在时抛出
            Exception: 解析过程中的其他错误
        """
        try:
            # 向后兼容性处理：忽略method参数，始终使用marker
            if method and method != "marker":
                logger.warning(f"Method '{method}' is deprecated. Using marker for all parsing.")
            
            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
            
            # 检查文件类型和支持格式
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Marker支持的文件格式 + 纯文本文件
            supported_formats = {
                # PDF文档
                '.pdf': 'pdf',
                # 图像文件
                '.png': 'image',
                '.jpg': 'image', 
                '.jpeg': 'image',
                '.bmp': 'image',
                '.tiff': 'image',
                '.tif': 'image',
                '.webp': 'image',
                # Office文档 (需要marker-pdf[full])
                '.docx': 'document',
                '.doc': 'document',
                '.pptx': 'document', 
                '.ppt': 'document',
                '.xlsx': 'document',
                '.xls': 'document',
                # 网页和电子书
                '.html': 'document',
                '.htm': 'document',
                '.epub': 'document',
                # 纯文本文件
                '.txt': 'text',
                '.md': 'text',
                '.markdown': 'text'
            }
            
            if file_extension not in supported_formats:
                raise ValueError(
                    f"Unsupported file format: {file_extension}. "
                    f"Supported formats: {', '.join(supported_formats.keys())}"
                )
            
            file_type = supported_formats[file_extension]
            
            # 如果没有提供元数据，创建基本元数据
            if metadata is None:
                metadata = {
                    "filename": os.path.basename(file_path),
                    "filetype": file_extension,
                    "filesize": os.path.getsize(file_path)
                }
            
            logger.info(f"Starting to parse {file_type} file: {file_path}")
            
            # 特殊处理纯文本文件
            if file_type == 'text':
                # 直接读取文本文件内容
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        markdown_text = f.read()
                except UnicodeDecodeError:
                    # 如果UTF-8失败，尝试其他编码
                    try:
                        with open(file_path, 'r', encoding='gbk') as f:
                            markdown_text = f.read()
                    except UnicodeDecodeError:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            markdown_text = f.read()
                
                # 对于.txt文件，如果不是markdown格式，我们可以稍作格式化
                if file_extension == '.txt':
                    # 保持原始格式，但确保有适当的换行
                    lines = markdown_text.split('\n')
                    # 如果文件很长且没有明显的段落分隔，添加一些格式化
                    if len(lines) == 1 and len(markdown_text) > 200:
                        # 长的单行文本，尝试在句号后分段
                        import re
                        markdown_text = re.sub(r'([。！？])\s*', r'\1\n\n', markdown_text)
                
                marker_metadata = {"source": "direct_text_read", "encoding_attempts": ["utf-8", "gbk", "latin-1"]}
                images = {}
                
                logger.info(f"Text file reading completed. Generated {len(markdown_text)} characters")
                
            else:
                # 根据文件类型选择合适的转换器
                converter = self._get_converter(file_type, file_extension)
                rendered = converter(file_path)
                
                # 提取markdown内容、元数据和图像
                markdown_text, marker_metadata, images = text_from_rendered(rendered)
                
                logger.info(f"Marker parsing completed. Generated {len(markdown_text)} characters of markdown")
            
            # 安全地处理图像信息
            image_count = 0
            if images:
                try:
                    image_count = len(images)
                except:
                    image_count = 0
            
            # 处理图像信息
            processed_images = []
            if images:
                try:
                    logger.info(f"Processing {image_count} images from document")
                    for i, (image_name, image_data) in enumerate(images.items()):
                        # 使用新的图像处理方法
                        image_info = self._process_image(
                            image_name=image_name,
                            image_data=image_data,
                            save_images=self.config.get("save_images", True),
                            include_base64=self.config.get("include_base64", False)
                        )
                        
                        if image_info and not image_info.get('error'):
                            processed_images.append(image_info)
                        else:
                            logger.warning(f"Failed to process image {image_name}: {image_info.get('error', 'Unknown error')}")
                            
                except Exception as img_error:
                    logger.error(f"Error processing images: {str(img_error)}")
                    # 继续处理，只是不添加图像信息
            
            # 在markdown中替换图像路径，保持原文档的位置结构
            if processed_images:
                logger.info("Replacing image paths in markdown to maintain original document structure")
                markdown_text = self._replace_image_paths_in_markdown(markdown_text, processed_images)
            
            # 构建解析内容 - 主要内容是更新后的markdown
            parsed_content = [{
                "type": "markdown",
                "content": markdown_text,
                "confidence": 0.95 if file_type != 'text' else 1.0,  # 文本文件是完全准确的
                "metadata": {
                    "source": "marker" if file_type != 'text' else "direct_text_read",
                    "converter_type": converter.__class__.__name__ if file_type != 'text' else "TextFileReader",
                    "file_type": file_type,
                    "images_extracted": image_count,
                    "images_processed": len(processed_images),
                    "image_paths_replaced": len(processed_images),
                    "marker_metadata": marker_metadata
                }
            }]
            
            # 为每个处理的图像添加单独的元数据块（用于详细信息记录）
            for image_info in processed_images:
                # 添加图像元数据块
                parsed_content.append({
                    "type": "image_metadata",
                    "content": f"Image metadata for: {image_info.get('image_name', '')}",
                    "confidence": 0.9,
                    "metadata": {
                        "image_name": image_info.get("image_name"),
                        "file_path": image_info.get("file_path"),
                        "format": image_info.get("format"),
                        "width": image_info.get("width"),
                        "height": image_info.get("height"),
                        "size_bytes": image_info.get("size"),
                        "base64_available": bool(image_info.get("base64")),
                        "base64_size": image_info.get("base64_size"),
                        "file_type": file_type
                    }
                })
                
                # 如果需要，添加base64内容块
                if image_info.get("base64") and self.config.get("include_base64", False):
                    parsed_content.append({
                        "type": "image_base64",
                        "content": image_info["base64"],
                        "confidence": 0.9,
                        "metadata": {
                            "image_name": image_info.get("image_name"),
                            "format": image_info.get("format"),
                            "encoding": "base64",
                            "size_bytes": image_info.get("size"),
                            "base64_size": image_info.get("base64_size")
                        }
                    })
            
            # 创建标准化的文档数据结构
            document_data = {
                "metadata": {
                    "filename": metadata.get("filename", ""),
                    "filetype": metadata.get("filetype", ""),
                    "filesize": metadata.get("filesize", 0),
                    "total_elements": len(parsed_content),
                    "parsing_method": "marker",
                    "file_type": file_type,
                    "parsing_config": {
                        "use_llm": self.use_llm if file_type != 'text' else False,
                        "force_ocr": self.force_ocr if file_type != 'text' else False,
                        "output_format": "markdown",
                        "save_images": self.config.get("save_images", True) if file_type != 'text' else False,
                        "include_base64": self.config.get("include_base64", True) if file_type != 'text' else False,
                        "extract_images": self.config.get("extract_images", True) if file_type != 'text' else False,
                        "converter_type": converter.__class__.__name__ if file_type != 'text' else "TextFileReader"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "marker_stats": {
                        "markdown_length": len(markdown_text),
                        "images_detected": image_count,
                        "images_processed": len(processed_images),
                        "images_saved": len([img for img in processed_images if img.get('file_path')]),
                        "images_with_base64": len([img for img in processed_images if img.get('base64')]),
                        "total_image_size_bytes": sum(img.get('size', 0) for img in processed_images),
                        "has_metadata": marker_metadata is not None
                    }
                },
                "content": parsed_content
            }
            
            # 保存解析结果
            self.save_document(document_data)
            
            logger.info(f"Document parsing completed successfully: {file_path}")
            return document_data
            
        except Exception as e:
            logger.error(f"Error in parse_document: {str(e)}")
            # 返回错误信息而不是抛出异常，保持接口兼容性
            
            # 尝试获取文件类型（用于错误响应）
            try:
                file_extension = os.path.splitext(file_path)[1].lower()
                supported_formats = {
                    '.pdf': 'pdf', '.png': 'image', '.jpg': 'image', '.jpeg': 'image',
                    '.bmp': 'image', '.tiff': 'image', '.tif': 'image', '.webp': 'image',
                    '.docx': 'document', '.doc': 'document', '.pptx': 'document', 
                    '.ppt': 'document', '.xlsx': 'document', '.xls': 'document',
                    '.html': 'document', '.htm': 'document', '.epub': 'document'
                }
                file_type = supported_formats.get(file_extension, 'unknown')
            except:
                file_extension = ""
                file_type = "unknown"
            
            error_document = {
                "metadata": {
                    "filename": metadata.get("filename", "") if metadata else os.path.basename(file_path) if os.path.exists(file_path) else "",
                    "filetype": file_extension,
                    "filesize": 0,
                    "total_elements": 1,
                    "parsing_method": "marker",
                    "file_type": file_type,
                    "parsing_config": {
                        "use_llm": self.use_llm,
                        "force_ocr": self.force_ocr,
                        "output_format": "markdown",
                        "save_images": self.config.get("save_images", True),
                        "include_base64": self.config.get("include_base64", True),
                        "extract_images": self.config.get("extract_images", True),
                        "converter_type": "unknown"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                },
                "content": [{
                    "type": "error",
                    "content": f"解析错误: {str(e)}",
                    "confidence": 0.0,
                    "metadata": {"error_type": type(e).__name__}
                }]
            }
            return error_document

    def save_document(self, document_data: Dict[str, Any]) -> str:
        """
        将解析的文档保存为JSON格式
        
        Args:
            document_data (Dict[str, Any]): 包含元数据和解析内容的文档数据字典
            
        Returns:
            str: 保存的文件路径
        """
        try:
            metadata = document_data.get("metadata", {})
            filename = metadata.get("filename", "unknown")
            parsing_method = metadata.get("parsing_method", "marker")
            
            # 构建文件名，包含时间戳避免重名
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            base_name = os.path.splitext(filename)[0]
            output_filename = f"{base_name}_{parsing_method}_{timestamp}.json"
            
            # 保存路径
            filepath = os.path.join("01-parsed-docs", output_filename)
            
            # 确保目录存在
            os.makedirs("01-parsed-docs", exist_ok=True)
            
            # 保存为JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Document saved to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            raise

    def parse_document_to_markdown(self, file_path: str) -> str:
        """
        直接解析文档并返回markdown字符串（便捷方法）
        
        Args:
            file_path (str): PDF文件路径
            
        Returns:
            str: markdown格式的文档内容
        """
        try:
            document_data = self.parse_document(file_path)
            
            # 从解析结果中提取markdown内容
            for content in document_data.get("content", []):
                if content.get("type") == "markdown":
                    return content.get("content", "")
            
            # 如果没找到markdown内容，返回空字符串
            return ""
            
        except Exception as e:
            logger.error(f"Error in parse_document_to_markdown: {str(e)}")
            return f"解析错误: {str(e)}"

    def get_parsing_stats(self) -> dict:
        """
        获取解析服务的状态信息
        
        Returns:
            dict: 包含配置和状态的信息字典
        """
        # 统计已初始化的converter数量
        converters_count = len(getattr(self, '_converters', {}))
        
        return {
            "service": "MarkerParsingService",
            "marker_available": MARKER_AVAILABLE,
            "converters_initialized": converters_count,
            "config": self.config.copy(),
            "supported_formats": {
                "pdf": [".pdf"],
                "images": [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"],
                "documents": [".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"],
                "web_ebooks": [".html", ".htm", ".epub"]
            },
            "output_format": "markdown",
            "features": [
                "高精度多格式文档解析",
                "PDF、图像、Office文档支持",
                "自动布局检测和阅读顺序识别",
                "高精度表格识别",
                "图像OCR和内容提取",
                "多语言支持",
                "LLM增强（可选）",
                "统一markdown输出"
            ]
        }

    def __del__(self):
        """
        清理资源
        """
        if hasattr(self, '_converters'):
            # marker的converter通常会自动清理资源
            self._converters.clear() 