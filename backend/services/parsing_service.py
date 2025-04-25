import logging
import os
import re
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import io

# PDF处理库
import fitz  # PyMuPDF
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.md import partition_md
from unstructured.partition.docx import partition_docx

# 图像处理库
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# 表格处理库
import pandas as pd
from img2table.ocr import TesseractOCR
from img2table.document import Image as Img2TableImage

logger = logging.getLogger(__name__)

class ParsingService:
    """
    文档解析服务类
    
    该类提供多种解析策略来提取和构建文档内容，支持：
    - PDF文档解析
    - Markdown文档解析
    - Word文档解析
    - 文本文档解析
    
    功能包括：
    - 表格识别与提取
    - 图像识别与OCR
    - 文档结构化解析
    - 内容分类
    """

    def __init__(self):
        """
        初始化解析服务
        """
        # 设置OCR代理为新的推荐方式
        os.environ["OCR_AGENT"] = "pytesseract"
        # 禁止从huggingface下载模型，避免SSL错误
        os.environ["UNSTRUCTURED_NO_DOWNLOAD_MODELS"] = "true"
        # 禁用下载YOLO模型
        os.environ["UNSTRUCTURED_LAYOUT_MODEL_ENABLED"] = "false"

        # 设置OCR语言，支持多语言
        self.ocr_lang = "chi_sim+eng"  # 中文简体+英文
        
        # 配置表格OCR
        self.table_ocr = TesseractOCR(n_threads=2, lang=self.ocr_lang)

    def parse_document(self, file_path: str, method: str, metadata: dict = None) -> dict:
        """
        解析文档文件并提取内容

        参数:
            file_path (str): 文档文件的路径
            method (str): 解析方法 ('all_in_one', 'structured', 'with_tables', 'with_images', 'with_tables_and_images')
            metadata (dict): 文档元数据，包括文件名和其他属性

        返回:
            dict: 解析后的文档数据，包括元数据和结构化内容

        异常:
            ValueError: 当文件不存在或指定了不支持的解析方法时抛出
        """
        try:
            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
            
            # 如果没有提供元数据，创建基本元数据
            if metadata is None:
                metadata = {
                    "filename": os.path.basename(file_path),
                    "filetype": os.path.splitext(file_path)[1].lower(),
                    "filesize": os.path.getsize(file_path)
                }
            
            # 根据文件类型选择解析器
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # 调用相应的解析方法
            if method == "all_in_one":
                parsed_content = self._parse_all_in_one(file_path, file_extension)
            elif method == "structured":
                parsed_content = self._parse_structured(file_path, file_extension)
            elif method == "with_tables":
                parsed_content = self._parse_with_tables(file_path, file_extension)
            elif method == "with_images":
                parsed_content = self._parse_with_images(file_path, file_extension)
            elif method == "with_tables_and_images":
                parsed_content = self._parse_with_tables_and_images(file_path, file_extension)
            else:
                raise ValueError(f"Unsupported parsing method: {method}")
            
            # 创建标准化的文档数据结构
            document_data = {
                "metadata": {
                    "filename": metadata.get("filename", ""),
                    "filetype": metadata.get("filetype", ""),
                    "filesize": metadata.get("filesize", 0),
                    "total_elements": len(parsed_content),
                    "parsing_method": method,
                    "timestamp": datetime.now().isoformat()
                },
                "content": parsed_content
            }
            
            return document_data
            
        except Exception as e:
            logger.error(f"Error in parse_document: {str(e)}")
            raise

    def _parse_all_in_one(self, file_path: str, file_extension: str) -> list:
        """
        将文档作为单一文本流解析

        参数:
            file_path (str): 文档文件的路径
            file_extension (str): 文件扩展名

        返回:
            list: 包含单一文本内容的列表
        """
        text = ""
        
        if file_extension == ".pdf":
            # 使用PyMuPDF提取PDF文本
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
        elif file_extension == ".md":
            # 解析Markdown文件
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif file_extension in [".docx", ".doc"]:
            # 使用unstructured解析Word文档
            elements = partition_docx(file_path)
            for element in elements:
                text += str(element.text) + "\n"
        else:
            # 默认作为文本文件读取
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                
        return [{
            "type": "text",
            "content": text,
            "page": 1,
            "confidence": 1.0
        }]

    def _parse_structured(self, file_path: str, file_extension: str) -> list:
        """
        将文档解析为结构化内容

        参数:
            file_path (str): 文档文件的路径
            file_extension (str): 文件扩展名

        返回:
            list: 包含结构化内容元素的列表
        """
        elements = []
        
        try:
            if file_extension == ".pdf":
                # 使用unstructured解析PDF
                try:
                    pdf_elements = partition_pdf(
                            filename=file_path, 
                            strategy="hi_res",
                        )
                    
                    # 调试输出
                    logger.debug(f"PDF解析元素数量: {len(pdf_elements) if pdf_elements else 0}")
                    
                    if not pdf_elements:
                        elements.append({
                            "type": "error",
                            "content": "解析PDF未返回任何元素",
                            "page": 1,
                            "confidence": 0.0
                        })
                        return elements
                        
                    for i, element in enumerate(pdf_elements):
                        try:
                            element_type = type(element).__name__.lower()
                            element_text = getattr(element, "text", "")
                            element_page = getattr(element, "page_number", i // 5 + 1)  # 估计页码
                            
                            if not element_text:
                                continue  # 跳过空文本元素
                                
                            if "title" in element_type:
                                elements.append({
                                    "type": "heading",
                                    "content": element_text,
                                    "page": element_page,
                                    "confidence": 0.95
                                })
                            elif "text" in element_type:
                                elements.append({
                                    "type": "text",
                                    "content": element_text,
                                    "page": element_page,
                                    "confidence": 0.9
                                })
                            elif "list" in element_type:
                                elements.append({
                                    "type": "list",
                                    "content": element_text,
                                    "page": element_page,
                                    "confidence": 0.85
                                })
                        except Exception as element_err:
                            logger.error(f"处理PDF元素时出错: {str(element_err)}")
                            continue  # 跳过处理失败的元素
                except Exception as pdf_err:
                    logger.error(f"调用partition_pdf时出错: {str(pdf_err)}")
                    # 如果元素为空，尝试使用PyMuPDF作为备选方案
                    if not elements:
                        try:
                            logger.info("使用PyMuPDF作为备选方案解析PDF")
                            pdf_doc = fitz.open(file_path)
                            
                            for page_num in range(len(pdf_doc)):
                                page = pdf_doc.load_page(page_num)
                                page_text = page.get_text()
                                
                                if page_text.strip():
                                    elements.append({
                                        "type": "text",
                                        "content": page_text,
                                        "page": page_num + 1,
                                        "confidence": 0.8
                                    })
                        except Exception as backup_err:
                            logger.error(f"备选方案也失败: {str(backup_err)}")
                            elements.append({
                                "type": "error",
                                "content": f"解析错误: {str(pdf_err)}; 备选方案也失败: {str(backup_err)}",
                                "page": 1,
                                "confidence": 0.0
                            })
            
            elif file_extension == ".md":
                # 解析Markdown文件
                md_elements = partition_md(file_path)
                for i, element in enumerate(md_elements):
                    element_type = type(element).__name__.lower()
                    
                    if "title" in element_type:
                        elements.append({
                            "type": "heading",
                            "content": element.text,
                            "page": 1,
                            "confidence": 1.0
                        })
                    elif "text" in element_type:
                        elements.append({
                            "type": "text",
                            "content": element.text,
                            "page": 1,
                            "confidence": 1.0
                        })
                    elif "list" in element_type:
                        elements.append({
                            "type": "list",
                            "content": element.text,
                            "page": 1,
                            "confidence": 1.0
                        })
            
            elif file_extension in [".docx", ".doc"]:
                # 解析Word文档
                docx_elements = partition_docx(file_path)
                for i, element in enumerate(docx_elements):
                    element_type = type(element).__name__.lower()
                    
                    if "title" in element_type:
                        elements.append({
                            "type": "heading",
                            "content": element.text,
                            "page": 1,
                            "confidence": 0.95
                        })
                    elif "text" in element_type:
                        elements.append({
                            "type": "text",
                            "content": element.text,
                            "page": 1,
                            "confidence": 0.9
                        })
                    elif "list" in element_type:
                        elements.append({
                            "type": "list",
                            "content": element.text,
                            "page": 1,
                            "confidence": 0.85
                        })
            
            else:
                # 默认作为文本处理
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    elements.append({
                        "type": "text",
                        "content": text,
                        "page": 1,
                        "confidence": 0.8
                    })
        
        except Exception as e:
            logger.error(f"Error in _parse_structured: {str(e)}")
            # 添加错误信息作为元素
            elements.append({
                "type": "error",
                "content": f"解析错误: {str(e)}",
                "page": 1,
                "confidence": 0.0
            })
        
        # 确保返回至少一个元素，即使是错误信息
        if not elements:
            elements.append({
                "type": "error",
                "content": "无法解析文档，未获取到任何内容",
                "page": 1,
                "confidence": 0.0
            })
            
        return elements

    def _parse_with_tables(self, file_path: str, file_extension: str) -> list:
        """
        解析文档，特别关注表格内容

        参数:
            file_path (str): 文档文件的路径
            file_extension (str): 文件扩展名

        返回:
            list: 包含文本和表格内容的列表
        """
        elements = []
        
        try:
            if file_extension == ".pdf":
                # 使用unstructured库提取表格（主要方法）
                try:
                    logger.info("使用unstructured提取PDF表格")
                    # 设置分区参数，优化表格检测
                    try:
                        # 尝试捕获特定的分区错误
                        pdf_elements = partition_pdf(
                            filename=file_path,
                            strategy="hi_res",
                            extract_images_in_pdf=False,  # 减少对图像的处理，专注于文本和表格
                            infer_table_structure=True,   # 保持表格结构推断
                            include_page_breaks=True,     # 添加页面分隔符，便于后续处理
                            pdf_image_dpi=300,            # 提高DPI，增强特殊符号识别
                        )
                    except TypeError as type_err:
                        # 可能是参数不兼容导致的，尝试使用更简单的参数调用
                        logger.warning(f"使用完整参数调用partition_pdf失败：{str(type_err)}，尝试使用简化参数")
                        pdf_elements = partition_pdf(
                            filename=file_path,
                            strategy="hi_res",
                        )
                    except ValueError as val_err:
                        # 值错误，可能与参数有关
                        logger.warning(f"partition_pdf值错误：{str(val_err)}，尝试使用简化参数")
                        pdf_elements = partition_pdf(
                            filename=file_path,
                        )
                    
                    # 验证返回的元素
                    if pdf_elements is None or not isinstance(pdf_elements, list):
                        logger.error("partition_pdf返回了非列表结果或空结果")
                        raise ValueError("partition_pdf未返回有效元素列表")
                    
                    logger.info(f"unstructured提取到{len(pdf_elements)}个元素")
                    
                    # 将文本元素和表格分开处理
                    text_elements = []
                    tables_found = False
                    tables_by_page = {}  # 按页码存储表格
                    
                    for i, element in enumerate(pdf_elements):
                        try:
                            element_type = type(element).__name__.lower()
                            element_page = getattr(element, "page_number", 1)
                            
                            # 处理表格元素
                            if "table" in element_type:
                                tables_found = True
                                
                                # 获取表格内容
                                table_content = ""
                                try:
                                    if hasattr(element, "text") and element.text:
                                        # 直接使用表格文本（可能是较简单的表格）
                                        table_content = element.text
                                    elif hasattr(element, "metadata") and element.metadata.get("text_as_html"):
                                        # 从HTML获取表格数据
                                        table_content = element.metadata.get("text_as_html")
                                    else:
                                        # 将表格转换为Markdown
                                        table_content = self._unstructured_table_to_markdown(element)
                                    
                                    if table_content and self._is_valid_table_content(table_content):
                                        # 创建表格元素
                                        table_element = {
                                            "type": "table",
                                            "content": table_content,
                                            "page": element_page,
                                            "confidence": 0.9,
                                            "metadata": f"Table on page {element_page}"
                                        }
                                        
                                        # 按页码存储表格
                                        if element_page not in tables_by_page:
                                            tables_by_page[element_page] = []
                                        tables_by_page[element_page].append(table_element)
                                        
                                        logger.info(f"成功提取表格: 页码 {element_page}")
                                except Exception as table_err:
                                    logger.error(f"处理unstructured表格时出错: {str(table_err)}")
                            
                            # 处理文本元素
                            elif hasattr(element, "text") and element.text.strip():
                                content_type = "text"
                                
                                # 确定内容类型
                                if "title" in element_type or "header" in element_type:
                                    content_type = "heading"
                                elif "list" in element_type:
                                    content_type = "list"
                                
                                text_elements.append({
                                    "type": content_type,
                                    "content": element.text,
                                    "page": element_page,
                                    "confidence": 0.85
                                })
                        except Exception as elem_err:
                            logger.error(f"处理单个unstructured元素时出错: {str(elem_err)}")
                            continue  # 跳过处理失败的元素
                    
                    # 将文本与对应页码的表格一起添加到elements
                    text_by_page = {}
                    for text_el in text_elements:
                        page = text_el["page"]
                        if page not in text_by_page:
                            text_by_page[page] = []
                        text_by_page[page].append(text_el)
                    
                    # 合并页面内容
                    all_pages = set(list(text_by_page.keys()) + list(tables_by_page.keys()))
                    for page in sorted(all_pages):
                        # 先添加表格
                        if page in tables_by_page:
                            elements.extend(tables_by_page[page])
                        
                        # 再添加文本
                        if page in text_by_page:
                            elements.extend(text_by_page[page])
                    
                    # 如果unstructured方法未找到表格，尝试使用PyMuPDF作为备选
                    if not tables_found:
                        logger.info("unstructured未找到表格，尝试使用PyMuPDF作为备选")
                        self._extract_tables_with_pymupdf(file_path, elements)
                
                except Exception as unstructured_err:
                    logger.error(f"使用unstructured提取表格失败: {str(unstructured_err)}")
                    logger.error(f"错误类型: {type(unstructured_err).__name__}")
                    # 记录更详细的回溯信息
                    import traceback
                    logger.error(f"详细错误: {traceback.format_exc()}")
                    
                    # 出错时尝试使用PyMuPDF作为备选
                    logger.info("回退到PyMuPDF方法")
                    self._extract_tables_with_pymupdf(file_path, elements)
                
                # 如果仍未找到表格，尝试使用图像表格提取方法
                if not any(e["type"] == "table" for e in elements):
                    logger.info("尝试使用图像表格提取方法作为最后备选")
                    self._extract_tables_from_pdf_images(file_path, elements)
            
            elif file_extension in [".docx", ".doc"]:
                # 使用unstructured处理Word文档
                docx_elements = partition_docx(file_path)
                
                for element in docx_elements:
                    element_type = type(element).__name__.lower()
                    
                    if "table" in element_type:
                        # 将表格转换为Markdown
                        table_md = element.metadata.get("text_as_html", "")
                        if not table_md:
                            table_md = str(element)
                        
                        # 检查表格是否为空
                        if table_md and "<td>" in table_md:  # 简单检查HTML表格是否有单元格
                            elements.append({
                                "type": "table",
                                "content": table_md,
                                "page": 1,
                                "confidence": 0.8,
                                "metadata": "Table from Word document"
                            })
                    else:
                        # 处理其他元素
                        content_type = "text"
                        if "title" in element_type:
                            content_type = "heading"
                        elif "list" in element_type:
                            content_type = "list"
                            
                        if hasattr(element, "text") and element.text.strip():
                            elements.append({
                                "type": content_type,
                                "content": element.text,
                                "page": 1,
                                "confidence": 0.9
                            })
            
            elif file_extension == ".md":
                # 处理Markdown文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    md_text = f.read()
                    
                # 提取表格（使用正则表达式识别Markdown表格）
                table_pattern = r'(\|[^\n]+\|(?:\n\|[^\n]+\|)+)'
                tables = re.findall(table_pattern, md_text)
                
                if tables:
                    remaining_text = md_text
                    valid_tables_count = 0
                    
                    for i, table in enumerate(tables):
                        # 验证表格是否包含实际内容
                        table_lines = table.split("\n")
                        has_content = False
                        for line in table_lines:
                            cells = [cell.strip() for cell in line.split("|")]
                            cells = [cell for cell in cells if cell]  # 过滤空单元格
                            if any(cells):
                                has_content = True
                                break
                                
                        if has_content:
                            # 添加表格
                            valid_tables_count += 1
                            elements.append({
                                "type": "table",
                                "content": table,
                                "page": 1,
                                "confidence": 1.0,
                                "metadata": f"Table {i+1} in Markdown"
                            })
                            remaining_text = remaining_text.replace(table, f"[TABLE_{i+1}]")
                    
                    # 添加剩余文本
                    if remaining_text.strip():
                        elements.append({
                            "type": "text",
                            "content": remaining_text,
                            "page": 1,
                            "confidence": 1.0
                        })
                else:
                    # 如果没有表格，添加全部文本
                    if md_text.strip():
                        elements.append({
                            "type": "text",
                            "content": md_text,
                            "page": 1,
                            "confidence": 1.0
                        })
            
            else:
                # 默认作为文本处理
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        if text.strip():
                            elements.append({
                                "type": "text",
                                "content": text,
                                "page": 1,
                                "confidence": 0.8
                            })
                except UnicodeDecodeError:
                    # 如果不是文本文件，添加错误消息
                    elements.append({
                        "type": "error",
                        "content": f"不支持的二进制文件类型: {file_extension}",
                        "page": 1,
                        "confidence": 0.0
                    })
        except Exception as e:
            logger.error(f"_parse_with_tables方法出错: {str(e)}")
            elements.append({
                "type": "error",
                "content": f"表格解析错误: {str(e)}",
                "page": 1,
                "confidence": 0.0
            })
        
        # 确保结果不为空
        if not elements:
            elements.append({
                "type": "error",
                "content": "未能从文档中提取任何内容",
                "page": 1,
                "confidence": 0.0
            })
                
        return elements

    def _parse_with_images(self, file_path: str, file_extension: str) -> list:
        """
        解析文档，特别关注图像内容

        参数:
            file_path (str): 文档文件的路径
            file_extension (str): 文件扩展名

        返回:
            list: 包含文本和图像内容的列表
        """
        elements = []
        
        try:
            if file_extension == ".pdf":
                # 使用PyMuPDF提取图像并进行OCR
                pdf_doc = fitz.open(file_path)
                
                for page_num in range(len(pdf_doc)):
                    page = pdf_doc.load_page(page_num)
                    page_text = page.get_text()
                    
                    # 提取图像
                    image_list = page.get_images(full=True)
                    
                    if image_list:
                        for img_index, img_info in enumerate(image_list):
                            try:
                                xref = img_info[0]
                                base_image = pdf_doc.extract_image(xref)
                                if not base_image:
                                    continue
                                    
                                image_bytes = base_image["image"]
                                
                                # 将图像转换为PIL图像
                                pil_image = Image.open(io.BytesIO(image_bytes))
                                
                                # 进行OCR
                                image_text = pytesseract.image_to_string(pil_image, lang=self.ocr_lang)
                                
                                if image_text.strip():
                                    elements.append({
                                        "type": "image_text",
                                        "content": image_text,
                                        "page": page_num + 1,
                                        "confidence": 0.7,
                                        "metadata": f"Image {img_index+1} on page {page_num+1}"
                                    })
                            except Exception as img_err:
                                logger.error(f"处理PDF中的图像时出错: {str(img_err)}")
                                elements.append({
                                    "type": "error",
                                    "content": f"图像处理错误: {str(img_err)}",
                                    "page": page_num + 1,
                                    "confidence": 0
                                })
                    
                    # 添加页面文本
                    if page_text:
                        elements.append({
                            "type": "text",
                            "content": page_text,
                            "page": page_num + 1,
                            "confidence": 0.9
                        })
                        
                # 回退方法：转换整个页面为图像并OCR
                if not elements:
                    temp_dir = tempfile.mkdtemp()
                    try:
                        images = convert_from_path(file_path)
                        
                        for i, image in enumerate(images):
                            # 保存图像
                            image_path = os.path.join(temp_dir, f"page_{i+1}.png")
                            image.save(image_path, "PNG")
                            
                            # OCR整页图像
                            image_text = pytesseract.image_to_string(Image.open(image_path), lang=self.ocr_lang)
                            
                            if image_text.strip():
                                elements.append({
                                    "type": "image_text",
                                    "content": image_text,
                                    "page": i + 1,
                                    "confidence": 0.6,
                                    "metadata": f"Full page OCR for page {i+1}"
                                })
                    except Exception as e:
                        logger.error(f"转换PDF页面为图像时出错: {str(e)}")
                        elements.append({
                            "type": "error",
                            "content": f"PDF转图像处理错误: {str(e)}",
                            "page": 1,
                            "confidence": 0
                        })
                    finally:
                        # 清理临时文件
                        import shutil
                        shutil.rmtree(temp_dir)
            
            elif file_extension in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]:
                # 直接对图像文件进行OCR
                image_text = pytesseract.image_to_string(Image.open(file_path), lang=self.ocr_lang)
                
                if image_text.strip():
                    elements.append({
                        "type": "image_text",
                        "content": image_text,
                        "page": 1,
                        "confidence": 0.8,
                        "metadata": "OCR result from image file"
                    })
            
            else:
                # 对于其他类型的文件，使用基本文本提取
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        elements.append({
                            "type": "text",
                            "content": text,
                            "page": 1,
                            "confidence": 0.8
                        })
                except Exception as text_err:
                    elements.append({
                        "type": "error",
                        "content": f"不支持的文件类型: {file_extension}，无法提取图像",
                        "page": 1,
                        "confidence": 0
                    })
        except Exception as e:
            logger.error(f"图像解析过程出错: {str(e)}")
            elements.append({
                "type": "error",
                "content": f"图像解析错误: {str(e)}",
                "page": 1,
                "confidence": 0
            })
                    
        return elements

    def _parse_with_tables_and_images(self, file_path: str, file_extension: str) -> list:
        """
        全面解析文档，包括文本、表格和图像

        参数:
            file_path (str): 文档文件的路径
            file_extension (str): 文件扩展名

        返回:
            list: 包含所有解析元素的列表
        """
        elements = []
        
        # 先解析表格
        table_elements = self._parse_with_tables(file_path, file_extension)
        elements.extend([e for e in table_elements if e["type"] == "table"])
        
        # 再解析图像
        image_elements = self._parse_with_images(file_path, file_extension)
        elements.extend([e for e in image_elements if e["type"] == "image_text"])
        
        # 最后添加文本
        text_elements = self._parse_structured(file_path, file_extension)
        
        # 过滤掉可能已经被表格或图像替代的内容
        for element in text_elements:
            if element["type"] not in ["table", "image", "image_text"]:
                elements.append(element)
        
        # 按页码和元素类型排序
        elements.sort(key=lambda x: (x["page"], self._element_type_priority(x["type"])))
        
        return elements

    def _element_type_priority(self, element_type: str) -> int:
        """
        获取元素类型的优先级，用于排序

        参数:
            element_type (str): 元素类型

        返回:
            int: 优先级值（数字越小优先级越高）
        """
        priorities = {
            "heading": 1,
            "table": 2,
            "image_text": 3,
            "list": 4,
            "text": 5,
            "error": 99
        }
        return priorities.get(element_type, 50)

    def _convert_table_to_markdown(self, table) -> str:
        """
        将表格转换为Markdown格式

        参数:
            table: PyMuPDF表格对象

        返回:
            str: Markdown格式的表格，如果表格为空则返回空字符串
        """
        try:
            # 获取表格数据
            rows = []
            for row in range(table.row_count):
                md_row = []
                for col in range(table.col_count):
                    try:
                        cell = table.cells[row * table.col_count + col]
                        # 检查单元格类型并安全获取文本
                        if cell is None:
                            cell_text = ""
                        elif isinstance(cell, tuple):
                            # 处理元组类型的单元格 (x0, y0, x1, y1, text, ...)
                            cell_text = cell[4] if len(cell) > 4 else ""
                        elif hasattr(cell, 'text'):
                            # 处理具有text属性的对象
                            cell_text = cell.text.strip()
                        else:
                            # 处理其他类型
                            cell_text = str(cell).strip()
                        
                        md_row.append(cell_text)
                    except Exception as cell_err:
                        logger.error(f"处理单元格时出错: {str(cell_err)}")
                        md_row.append("")
                rows.append(md_row)
            
            if not rows:
                return ""
            
            # 检查表格是否实际包含内容
            has_content = False
            for row in rows:
                if any(cell.strip() for cell in row):
                    has_content = True
                    break
                    
            if not has_content:
                logger.warning("检测到空表格，不生成Markdown")
                return ""
                
            # 构建Markdown表格
            md_table = []
            
            # 表头
            md_table.append("| " + " | ".join(rows[0]) + " |")
            
            # 分隔行
            md_table.append("| " + " | ".join(["---"] * len(rows[0])) + " |")
            
            # 数据行
            for row in rows[1:]:
                md_table.append("| " + " | ".join(row) + " |")
                
            return "\n".join(md_table)
        except Exception as e:
            logger.error(f"Error converting table to Markdown: {e}")
            return f"Error extracting table: {str(e)}"

    def _extract_tables_with_pymupdf(self, file_path: str, elements: list):
        """
        使用PyMuPDF提取PDF表格的辅助方法
        
        参数:
            file_path: PDF文件路径
            elements: 解析元素列表，将向其中添加提取的表格
        """
        try:
            # 使用PyMuPDF获取页面
            pdf_doc = fitz.open(file_path)
            
            # 检查PyMuPDF版本并记录
            pymupdf_version_str = getattr(fitz, "version", ["0.0.0"])[0]
            logger.info(f"当前PyMuPDF版本: {pymupdf_version_str}")
            
            # 解析版本字符串
            try:
                pymupdf_version = tuple(map(int, pymupdf_version_str.split(".")))
            except (ValueError, AttributeError):
                # 如果版本解析失败，使用默认版本
                logger.warning(f"无法解析PyMuPDF版本: {pymupdf_version_str}，使用默认版本")
                pymupdf_version = (0, 0, 0)
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                page_text = page.get_text()
                
                # 提取表格
                try:
                    # 安全地检查find_tables方法是否存在
                    if not hasattr(page, "find_tables"):
                        logger.warning("当前PyMuPDF版本不支持find_tables方法，无法提取表格")
                        # 只添加文本并继续
                        if page_text.strip():
                            elements.append({
                                "type": "text",
                                "content": page_text,
                                "page": page_num + 1,
                                "confidence": 0.9
                            })
                        continue
                    
                    # 根据版本使用不同的参数调用find_tables
                    tables = None
                    
                    try:
                        # 尝试使用基本参数
                        if pymupdf_version >= (1, 18, 0):
                            # 1.18.0及以上版本支持策略参数
                            tables = page.find_tables()
                        else:
                            # 旧版本使用默认调用
                            tables = page.find_tables()
                    except Exception as table_err:
                        logger.error(f"尝试使用标准参数提取表格时出错: {str(table_err)}")
                        # 尝试更简单的调用
                        try:
                            tables = page.find_tables()
                        except Exception as simple_err:
                            logger.error(f"无法使用任何方法提取表格: {str(simple_err)}")
                            tables = None
                    
                    # 处理找到的表格
                    valid_tables_count = 0
                    if tables and hasattr(tables, "tables") and tables.tables:
                        for i, table in enumerate(tables.tables):
                            try:
                                # 检查表格是否有效
                                if not hasattr(table, "row_count") or not hasattr(table, "col_count"):
                                    logger.warning(f"表格{i+1}格式无效，跳过")
                                    continue
                                    
                                # 检查表格是否足够大
                                if table.row_count < 2 or table.col_count < 2:
                                    logger.debug(f"跳过小表格: 第{page_num+1}页表格{i+1} (行:{table.row_count}, 列:{table.col_count})")
                                    continue
                                    
                                # 将表格转换为Markdown格式
                                markdown_table = self._convert_table_to_markdown(table)
                                
                                if markdown_table:
                                    valid_tables_count += 1
                                    elements.append({
                                        "type": "table",
                                        "content": markdown_table,
                                        "page": page_num + 1,
                                        "confidence": 0.85,
                                        "metadata": f"PyMuPDF Table {i+1} on page {page_num+1}"
                                    })
                                    logger.info(f"PyMuPDF成功提取表格: 第{page_num+1}页表格{i+1}")
                                else:
                                    logger.warning(f"PyMuPDF表格转换失败或为空: 第{page_num+1}页的表格{i+1}")
                            except Exception as table_err:
                                logger.error(f"处理PyMuPDF表格时出错: {str(table_err)}")
                    else:
                        logger.info(f"第{page_num+1}页未找到表格")
                                
                    # 添加页面文本(不管是否有表格都添加，确保内容完整)
                    if page_text.strip():
                        elements.append({
                            "type": "text",
                            "content": page_text,
                            "page": page_num + 1,
                            "confidence": 0.9
                        })
                except Exception as page_table_err:
                    logger.error(f"提取第{page_num+1}页表格时出错: {str(page_table_err)}")
                    # 出错时也添加文本，避免内容丢失
                    if page_text.strip():
                        elements.append({
                            "type": "text",
                            "content": page_text,
                            "page": page_num + 1,
                            "confidence": 0.9
                        })
        except Exception as e:
            logger.error(f"PyMuPDF提取表格出错: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            
    def _extract_tables_from_image(self, image_path: str) -> List[str]:
        """
        从图像中提取表格

        参数:
            image_path (str): 图像文件路径

        返回:
            List[str]: 提取的表格（Markdown格式）列表
        """
        try:
            # 确保pandas可用
            import pandas as pd
            
            # 加载图像
            img = Img2TableImage(image_path)
            
            # 提取表格
            tables = img.extract_tables(
                ocr=self.table_ocr,
                borderless_tables=True,  # 检测无边框表格
                min_confidence=60        # 最小置信度
            )
            
            md_tables = []
            
            for i, table in enumerate(tables):
                try:
                    # 检查表格是否有效
                    if not hasattr(table, 'df') or table.df is None or table.df.empty:
                        logger.warning(f"提取的表格 {i+1} 无效或为空")
                        continue
                    
                    # 检查表格是否足够大，跳过过小的表格
                    if table.df.shape[0] < 2 or table.df.shape[1] < 2:
                        logger.debug(f"跳过小表格: 表格{i+1} (行:{table.df.shape[0]}, 列:{table.df.shape[1]})")
                        continue
                        
                    # 检查表格内容是否为空
                    has_content = False
                    for row_idx in range(table.df.shape[0]):
                        for col_idx in range(table.df.shape[1]):
                            cell_value = table.df.iloc[row_idx, col_idx]
                            if pd.notna(cell_value) and str(cell_value).strip():
                                has_content = True
                                break
                        if has_content:
                            break
                    
                    if not has_content:
                        logger.warning(f"表格 {i+1} 没有实际内容，跳过")
                        continue
                        
                    # 将表格转换为Markdown
                    rows = []
                    
                    for row_idx in range(table.df.shape[0]):
                        row_data = []
                        for col_idx in range(table.df.shape[1]):
                            try:
                                cell_value = table.df.iloc[row_idx, col_idx]
                                # 替换空值
                                if pd.isna(cell_value):
                                    cell_value = ""
                                # 处理各种类型的单元格值
                                elif isinstance(cell_value, (list, tuple)):
                                    # 如果是列表或元组，取第一个非空元素或使用空格
                                    cell_value = next((item for item in cell_value if item), "")
                                
                                # 转换为字符串并清理
                                cell_text = str(cell_value).strip()
                                # 替换Markdown表格中的特殊字符
                                cell_text = cell_text.replace("|", "\\|").replace("\n", " ")
                                row_data.append(cell_text)
                            except Exception as cell_err:
                                logger.error(f"处理表格单元格时出错: {str(cell_err)}")
                                row_data.append("")
                        
                        if row_data and any(cell.strip() for cell in row_data):  # 只添加有数据的行
                            rows.append(row_data)
                    
                    if not rows:
                        logger.warning(f"表格 {i+1} 没有有效行")
                        continue
                        
                    # 确保所有行有相同数量的列
                    max_cols = max(len(row) for row in rows)
                    for row in rows:
                        while len(row) < max_cols:
                            row.append("")
                    
                    # 构建Markdown表格
                    md_table = []
                    
                    # 表头
                    md_table.append("| " + " | ".join(rows[0]) + " |")
                    
                    # 分隔行
                    md_table.append("| " + " | ".join(["---"] * max_cols) + " |")
                    
                    # 数据行
                    for row in rows[1:]:
                        md_table.append("| " + " | ".join(row) + " |")
                    
                    # 最终检查生成的表格是否有内容
                    table_content = "\n".join(md_table)
                    # 提取所有单元格内容进行检查
                    all_cells = []
                    for line in table_content.split("\n"):
                        if line.startswith("|") and "---" not in line:  # 跳过分隔行
                            cells = [cell.strip() for cell in line.split("|")]
                            all_cells.extend([cell for cell in cells if cell])
                    
                    # 检查是否有有效单元格内容
                    if any(all_cells):
                        md_tables.append(table_content)
                        logger.info(f"成功从图像提取表格 {i+1}")
                    else:
                        logger.warning(f"生成的Markdown表格 {i+1} 没有内容，跳过")
                        
                except Exception as table_err:
                    logger.error(f"处理图像表格 {i+1} 时出错: {str(table_err)}")
                
            return md_tables
        except Exception as e:
            logger.error(f"从图像提取表格时出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return []

    def _unstructured_table_to_markdown(self, table_element) -> str:
        """
        将unstructured库的表格元素转换为Markdown格式
        
        参数:
            table_element: unstructured表格元素
            
        返回:
            str: Markdown格式的表格
        """
        try:
            # 获取表格数据
            if not hasattr(table_element, "metadata") or not table_element.metadata:
                logger.debug("表格元素没有metadata属性")
                # 尝试直接从text属性获取文本
                if hasattr(table_element, "text") and table_element.text:
                    lines = table_element.text.strip().split("\n")
                    if len(lines) > 1:
                        # 将文本转换为可能的表格形式
                        return self._text_to_markdown_table(lines)
                return ""
            
            # 详细记录元素属性，帮助调试
            logger.debug(f"表格元素类型: {type(table_element).__name__}")
            logger.debug(f"表格元素属性: {dir(table_element)}")
            if hasattr(table_element, "metadata"):
                logger.debug(f"表格元素元数据: {table_element.metadata.keys() if table_element.metadata else 'None'}")
            
            # 尝试从元数据中获取表格结构
            table_data = None
            
            # 方法1：从HTML中提取表格数据
            if hasattr(table_element, "metadata") and table_element.metadata and "text_as_html" in table_element.metadata:
                html_content = table_element.metadata["text_as_html"]
                if html_content and "<table" in html_content:
                    try:
                        # 使用正则表达式提取表格内容
                        import re
                        # 提取行
                        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_content, re.DOTALL)
                        if rows:
                            table_data = []
                            for row in rows:
                                # 提取单元格（同时处理th和td）
                                cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.DOTALL)
                                if cells:
                                    # 替换HTML实体和标签
                                    cleaned_cells = []
                                    for cell in cells:
                                        # 移除HTML标签
                                        cell = re.sub(r'<[^>]+>', ' ', cell)
                                        # 替换常见HTML实体
                                        cell = cell.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
                                        cleaned_cells.append(cell.strip())
                                    table_data.append(cleaned_cells)
                    except Exception as html_err:
                        logger.error(f"从HTML提取表格数据时出错: {str(html_err)}")
            
            # 方法2：检查cells属性
            if not table_data and hasattr(table_element, "cells"):
                try:
                    # 安全获取cells属性
                    cells = table_element.cells
                    if isinstance(cells, list) and cells:
                        # 处理可能的不同cells格式
                        table_data = []
                        for row in cells:
                            if isinstance(row, list):
                                # 如果行本身就是列表，直接使用
                                row_data = []
                                for cell in row:
                                    # 处理单元格
                                    if hasattr(cell, 'text'):
                                        row_data.append(cell.text)
                                    else:
                                        row_data.append(str(cell))
                                table_data.append(row_data)
                            elif isinstance(cells[0], list):
                                # 如果cells是二维列表
                                table_data = cells
                                break
                except Exception as cells_err:
                    logger.error(f"从cells属性提取表格数据时出错: {str(cells_err)}")
            
            # 方法3：从文本属性解析表格
            if not table_data and hasattr(table_element, "text") and table_element.text:
                try:
                    text_lines = table_element.text.strip().split("\n")
                    if len(text_lines) > 1:
                        return self._text_to_markdown_table(text_lines)
                except Exception as text_err:
                    logger.error(f"从文本解析表格时出错: {str(text_err)}")
            
            # 如果我们没有有效的表格数据，返回空字符串
            if not table_data or not any(row for row in table_data if row):
                logger.warning("无法从unstructured表格元素提取有效数据")
                return ""
            
            # 确保所有行具有相同的列数
            if table_data:
                max_cols = max(len(row) for row in table_data if row)
                for i, row in enumerate(table_data):
                    if len(row) < max_cols:
                        table_data[i] = row + [""] * (max_cols - len(row))
                
                # 构建Markdown表格
                md_table = []
                
                # 表头（第一行）
                md_table.append("| " + " | ".join(str(cell or '') for cell in table_data[0]) + " |")
                
                # 分隔行
                md_table.append("| " + " | ".join(["---"] * max_cols) + " |")
                
                # 数据行
                for row in table_data[1:]:
                    md_table.append("| " + " | ".join(str(cell or '') for cell in row) + " |")
                
                return "\n".join(md_table)
            
            return ""
        except Exception as e:
            logger.error(f"转换unstructured表格为Markdown时出错: {str(e)}")
            # 记录详细错误信息
            import traceback
            logger.error(f"表格转换错误详情: {traceback.format_exc()}")
            return ""
            
    def _text_to_markdown_table(self, text_lines: list) -> str:
        """
        将文本行转换为Markdown表格格式
        
        参数:
            text_lines: 文本行列表
            
        返回:
            str: Markdown格式的表格
        """
        try:
            # 预处理：查找每行的分隔符
            # 常见分隔符包括制表符、多个空格、|符号等
            
            # 检查是否已经是Markdown表格格式（包含 | 符号）
            if any("|" in line for line in text_lines):
                # 如果已经是带|的格式，做简单标准化
                md_lines = []
                for line in text_lines:
                    # 确保行首尾有|
                    if not line.startswith("|"):
                        line = "| " + line
                    if not line.endswith("|"):
                        line = line + " |"
                    md_lines.append(line)
                
                # 确保有分隔行
                has_separator = False
                for i, line in enumerate(md_lines):
                    if i > 0 and all(c == '-' or c == '|' or c.isspace() for c in line):
                        has_separator = True
                        break
                
                if not has_separator and len(md_lines) > 1:
                    # 添加分隔行
                    header = md_lines[0]
                    col_count = header.count("|") - 1
                    separator = "| " + " | ".join(["---"] * col_count) + " |"
                    md_lines.insert(1, separator)
                
                return "\n".join(md_lines)
            
            # 检测是否以制表符分隔
            if any("\t" in line for line in text_lines):
                return self._convert_delimited_text_to_markdown(text_lines, "\t")
            
            # 检测是否以多个空格分隔（这是启发式的，可能不准确）
            # 查看第一行是否有明显的空白间隔
            if len(text_lines) > 0:
                first_line = text_lines[0]
                spaces_pattern = re.compile(r"\s{2,}")
                if spaces_pattern.search(first_line):
                    # 可能是空格分隔的表格，尝试分割
                    return self._convert_space_delimited_text_to_markdown(text_lines)
            
            # 如果没有明显的分隔符，使用简单的空格分割
            return self._convert_delimited_text_to_markdown(text_lines, " ")
        except Exception as e:
            logger.error(f"文本转Markdown表格时出错: {str(e)}")
            return ""
    
    def _convert_delimited_text_to_markdown(self, text_lines: list, delimiter: str) -> str:
        """
        将有分隔符的文本转换为Markdown表格
        
        参数:
            text_lines: 文本行列表
            delimiter: 分隔符
            
        返回:
            str: Markdown格式的表格
        """
        if not text_lines:
            return ""
            
        table_data = []
        for line in text_lines:
            if line.strip():  # 跳过空行
                row = [cell.strip() for cell in line.split(delimiter)]
                table_data.append(row)
        
        if not table_data:
            return ""
            
        # 确保所有行有相同数量的列
        max_cols = max(len(row) for row in table_data)
        for i, row in enumerate(table_data):
            if len(row) < max_cols:
                table_data[i] = row + [""] * (max_cols - len(row))
        
        # 构建Markdown表格
        md_table = []
        
        # 表头
        md_table.append("| " + " | ".join(table_data[0]) + " |")
        
        # 分隔行
        md_table.append("| " + " | ".join(["---"] * max_cols) + " |")
        
        # 数据行
        for row in table_data[1:]:
            md_table.append("| " + " | ".join(row) + " |")
            
        return "\n".join(md_table)
    
    def _convert_space_delimited_text_to_markdown(self, text_lines: list) -> str:
        """
        将空格分隔的文本转换为Markdown表格
        
        参数:
            text_lines: 文本行列表
            
        返回:
            str: Markdown格式的表格
        """
        if not text_lines:
            return ""
        
        # 尝试找出列的位置，基于第一行
        first_line = text_lines[0]
        # 寻找有2个或更多连续空格的位置，这可能是列分隔
        col_positions = []
        i = 0
        while i < len(first_line):
            if first_line[i].isspace():
                start = i
                while i < len(first_line) and first_line[i].isspace():
                    i += 1
                if i - start >= 2:  # 至少2个连续空格
                    col_positions.append((start, i))
            else:
                i += 1
        
        # 如果没有找到足够的分隔位置，使用简单分割
        if len(col_positions) == 0:
            return self._convert_delimited_text_to_markdown(text_lines, " ")
        
        # 根据列位置分割每行
        table_data = []
        for line in text_lines:
            if not line.strip():  # 跳过空行
                continue
                
            row = []
            last_end = 0
            for start, end in col_positions:
                # 添加列之前的内容
                if start > last_end:
                    row.append(line[last_end:start].strip())
                last_end = end
            
            # 添加最后一个分隔符之后的内容
            if last_end < len(line):
                row.append(line[last_end:].strip())
                
            # 确保至少有一个单元格
            if not row:
                row = [line.strip()]
                
            table_data.append(row)
        
        if not table_data:
            return ""
            
        # 确保所有行有相同数量的列
        max_cols = max(len(row) for row in table_data)
        for i, row in enumerate(table_data):
            if len(row) < max_cols:
                table_data[i] = row + [""] * (max_cols - len(row))
        
        # 构建Markdown表格
        md_table = []
        
        # 表头
        md_table.append("| " + " | ".join(table_data[0]) + " |")
        
        # 分隔行
        md_table.append("| " + " | ".join(["---"] * max_cols) + " |")
        
        # 数据行
        for row in table_data[1:]:
            md_table.append("| " + " | ".join(row) + " |")
            
        return "\n".join(md_table)

    def _is_valid_table_content(self, content: str) -> bool:
        """
        检查表格内容是否有效
        
        参数:
            content: 表格内容（Markdown或HTML格式）
            
        返回:
            bool: 内容是否有效
        """
        if not content or content.isspace():
            return False
            
        # 检查Markdown表格
        if content.startswith("|"):
            # 提取所有单元格内容
            cells = []
            for line in content.split("\n"):
                if "|" in line and "---" not in line:  # 跳过分隔行
                    line_cells = [cell.strip() for cell in line.split("|")]
                    cells.extend([cell for cell in line_cells if cell])
            
            # 检查是否有有效单元格内容
            return any(cell for cell in cells if cell and not cell.isspace())
        
        # 检查HTML表格
        elif "<table" in content:
            # 简单检查是否有单元格内容
            return "<td>" in content and not all(part.isspace() for part in content.split("<td>")[1:])
        
        # 普通文本，检查是否有内容
        else:
            return any(line.strip() for line in content.split("\n"))

    def _extract_tables_from_pdf_images(self, file_path: str, elements: list):
        """
        通过PDF转图像方式提取表格的辅助方法
        
        参数:
            file_path: PDF文件路径
            elements: 解析元素列表，将向其中添加提取的表格
        """
        temp_dir = tempfile.mkdtemp()
        try:
            # 将PDF转换为图像
            images = convert_from_path(file_path)
            
            for i, image in enumerate(images):
                # 保存图像
                image_path = os.path.join(temp_dir, f"page_{i+1}.png")
                image.save(image_path, "PNG")
                
                try:
                    # 提取表格
                    img_tables = self._extract_tables_from_image(image_path)
                    
                    for j, table_md in enumerate(img_tables):
                        if table_md and not table_md.startswith("Error") and "|" in table_md:
                            # 验证表格是否包含实际内容
                            table_lines = table_md.split("\n")
                            if len(table_lines) > 2:  # 至少有表头、分隔线和一行数据
                                has_content = False
                                for line in table_lines:
                                    cells = [cell.strip() for cell in line.split("|")]
                                    cells = [cell for cell in cells if cell]  # 过滤空单元格
                                    if any(cells):
                                        has_content = True
                                        break
                                        
                                if has_content:
                                    elements.append({
                                        "type": "table",
                                        "content": table_md,
                                        "page": i + 1,
                                        "confidence": 0.75,
                                        "metadata": f"Image-extracted Table {j+1} on page {i+1}"
                                    })
                                    logger.info(f"成功从图像提取表格: 第{i+1}页表格{j+1}")
                except Exception as img_table_err:
                    logger.error(f"从图像提取表格时出错: {str(img_table_err)}")
                    import traceback
                    logger.error(f"详细错误: {traceback.format_exc()}")
        except Exception as convert_err:
            logger.error(f"PDF转图像失败: {str(convert_err)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
        finally:
            # 清理临时文件
            import shutil
            shutil.rmtree(temp_dir)

import io  # 添加缺失的导入 