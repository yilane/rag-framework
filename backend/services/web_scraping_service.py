import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

# 修复导入路径 - 使用相对导入
try:
    from ..utils.logger import logger
except ImportError:
    # 如果相对导入失败，使用标准logging作为后备
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

# 导入 trafilatura 核心模块
try:
    import trafilatura
    from trafilatura import fetch_url, extract, extract_metadata
    from trafilatura.feeds import find_feed_urls
    from trafilatura.sitemaps import sitemap_search
    from trafilatura.spider import focused_crawler
    TRAFILATURA_AVAILABLE = True
except ImportError:
    trafilatura = None
    TRAFILATURA_AVAILABLE = False
    logger.error("trafilatura not available. Please install: pip install trafilatura[all]")

# 备选方案导入
try:
    import requests
    from bs4 import BeautifulSoup
    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False


class WebScrapingService:
    """
    基于 Trafilatura 的高效网页抓取服务
    
    功能特点：
    1. 专业级内容提取 - 使用学术级基准测试第一的trafilatura
    2. 多种输出格式 - 支持Markdown, JSON, XML, HTML, TXT
    3. 智能元数据提取 - 自动提取标题、作者、日期等
    4. RSS/Sitemap发现 - 自动发现和处理feeds
    5. 聚焦爬虫 - 智能网站内容发现
    6. 批量处理 - 高效并发处理
    7. 保存到01-parsed-docs目录
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化网页抓取服务
        
        Args:
            config: 配置选项
        """
        if not TRAFILATURA_AVAILABLE:
            raise ImportError("trafilatura is required but not installed. Run: pip install trafilatura[all]")
        
        self.config = config or {}
        
        # 输出格式配置 - 必须先定义这些属性
        self.default_output_format = self.config.get("output_format", "markdown")
        self.include_metadata = self.config.get("include_metadata", True)
        self.include_comments = self.config.get("include_comments", False)
        self.include_tables = self.config.get("include_tables", True)
        self.include_links = self.config.get("include_links", True)
        self.include_images = self.config.get("include_images", False)
        
        # 网络配置
        self.timeout = self.config.get("timeout", 30)
        self.max_redirects = self.config.get("max_redirects", 10)
        self.user_agent = self.config.get(
            "user_agent", 
            "TrafilaturaBot/2.0 (+https://github.com/adbar/trafilatura)"
        )
        
        # 抓取限制
        self.max_content_length = self.config.get("max_content_length", 20 * 1024 * 1024)  # 20MB
        self.min_text_length = self.config.get("min_text_length", 100)
        
        # 语言过滤
        self.target_language = self.config.get("target_language", None)  # 例如: 'zh', 'en'
        
        # 高级选项
        self.favor_precision = self.config.get("favor_precision", False)
        self.favor_recall = self.config.get("favor_recall", False)
        self.no_fallback = self.config.get("no_fallback", False)  # 快速模式
        
        logger.info("WebScrapingService initialized with trafilatura")
        logger.info(f"Default output format: {self.default_output_format}")
    
    def scrape_webpage(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        使用 trafilatura 进行网页抓取和解析
        
        Args:
            url: 网页URL
            **kwargs: 额外的提取参数
                - output_format: 输出格式 ('markdown', 'json', 'xml', 'html', 'txt')
                - include_metadata: 是否包含元数据
                - include_comments: 是否包含评论
                - include_tables: 是否包含表格
                - include_links: 是否包含链接
                - favor_precision: 优先精确度
                - favor_recall: 优先召回率
                - no_fallback: 快速模式
                
        Returns:
            解析后的文档数据
        """
        try:
            start_time = time.time()
            logger.info(f"开始抓取网页: {url}")
            
            # 1. 下载网页内容
            downloaded = fetch_url(url)
            if not downloaded:
                raise ValueError(f"无法下载网页内容: {url}")
            
            # 2. 合并提取参数
            extract_options = self._prepare_extract_options(**kwargs)
            
            # 3. 提取主要内容
            content = extract(
                downloaded,
                output_format=kwargs.get('output_format', self.default_output_format),
                with_metadata=extract_options['with_metadata'],
                include_comments=extract_options['include_comments'],
                include_tables=extract_options['include_tables'],
                include_links=extract_options['include_links'],
                include_images=extract_options['include_images'],
                no_fallback=extract_options['no_fallback'],
                favor_precision=extract_options['favor_precision'],
                favor_recall=extract_options['favor_recall'],
                target_language=extract_options['target_language'],
                url=url  # 传递URL用于相对链接转换和日期提取
            )
            
            if not content:
                raise ValueError("无法提取网页内容")
            
            # 4. 提取元数据
            if self.include_metadata:
                try:
                    metadata_result = extract_metadata(downloaded)
                    # 确保metadata是字典类型
                    if isinstance(metadata_result, dict):
                        metadata = metadata_result
                    else:
                        metadata = {}
                        logger.warning(f"extract_metadata返回了非字典类型: {type(metadata_result)}")
                except Exception as e:
                    logger.warning(f"提取元数据失败: {str(e)}")
                    metadata = {}
            else:
                metadata = {}
            
            # 5. 计算处理时间
            processing_time = time.time() - start_time
            
            # 6. 构建文档数据
            document_data = self._build_document_data(
                url=url,
                content=content,
                metadata=metadata,
                processing_time=processing_time,
                extract_options=extract_options
            )
            
            # 7. 保存文档
            filepath = self.save_document(document_data)
            document_data['saved_path'] = filepath
            
            logger.info(f"网页抓取完成: {url} ({processing_time:.2f}秒)")
            return document_data
            
        except Exception as e:
            logger.error(f"网页抓取失败 {url}: {str(e)}")
            return self._create_error_document(url, str(e))
    
    def _prepare_extract_options(self, **kwargs) -> dict:
        """准备提取选项"""
        options = {}
        
        # 使用默认配置 - 使用正确的属性名
        options['with_metadata'] = kwargs.get('include_metadata', self.include_metadata)
        options['include_comments'] = kwargs.get('include_comments', self.include_comments)
        options['include_tables'] = kwargs.get('include_tables', self.include_tables)
        options['include_links'] = kwargs.get('include_links', self.include_links)
        options['include_images'] = kwargs.get('include_images', self.include_images)
        
        # 性能选项
        options['no_fallback'] = kwargs.get('no_fallback', self.no_fallback)
        options['favor_precision'] = kwargs.get('favor_precision', self.favor_precision)
        options['favor_recall'] = kwargs.get('favor_recall', self.favor_recall)
        
        # 语言选项
        options['target_language'] = kwargs.get('target_language', self.target_language)
        
        return options
    
    def _build_document_data(self, url: str, content: str, metadata: dict, 
                           processing_time: float, extract_options: dict) -> Dict[str, Any]:
        """构建标准化的文档数据结构"""
        
        # 生成文件名
        filename = self._generate_filename(url, metadata.get('title', ''))
        
        # 确定内容类型 - 使用默认输出格式
        content_type = self.default_output_format
        if content_type == 'markdown':
            content_type = 'markdown'
        elif content_type == 'json':
            content_type = 'json'
        elif content_type in ['xml', 'xmltei']:
            content_type = 'xml'
        else:
            content_type = 'text'
        
        # 构建解析内容
        parsed_content = [{
            "type": content_type,
            "content": content,
            "confidence": 0.95,  # trafilatura 的高置信度
            "page": 1,
            "metadata": {
                "source": "trafilatura",
                "extraction_method": "trafilatura_extract",
                "url": url,
                "output_format": self.default_output_format,
                "processing_time": processing_time,
                **metadata
            }
        }]
        
        # 计算统计信息
        word_count = len(content.split()) if content else 0
        char_count = len(content) if content else 0
        
        # 构建完整文档数据
        document_data = {
            "metadata": {
                "filename": filename,
                "filetype": ".html",
                "filesize": len(content.encode('utf-8')) if content else 0,
                "total_elements": 1,
                "parsing_method": "trafilatura",
                "file_type": "webpage",
                "parsing_config": extract_options,
                "timestamp": datetime.now().isoformat(),
                "trafilatura_metadata": metadata,
                "extraction_stats": {
                    "original_url": url,
                    "processing_time": processing_time,
                    "content_length": len(content) if content else 0,
                    "word_count": word_count,
                    "char_count": char_count,
                    "extraction_success": bool(content)
                }
            },
            "content": parsed_content
        }
        
        return document_data
    
    def _create_error_document(self, url: str, error_message: str) -> Dict[str, Any]:
        """创建错误文档"""
        filename = self._generate_filename(url, "error")
        
        return {
            "metadata": {
                "filename": filename,
                "filetype": ".html",
                "filesize": 0,
                "total_elements": 1,
                "parsing_method": "trafilatura",
                "file_type": "webpage",
                "timestamp": datetime.now().isoformat(),
                "error": error_message,
                "original_url": url
            },
            "content": [{
                "type": "error",
                "content": f"网页解析错误: {error_message}",
                "confidence": 0.0,
                "page": 1,
                "metadata": {
                    "error_type": "extraction_failed",
                    "url": url,
                    "source": "trafilatura"
                }
            }]
        }
    
    def _generate_filename(self, url: str, title: str = "") -> str:
        """生成安全的文件名"""
        try:
            from urllib.parse import urlparse
            import re
            
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")
            
            if title:
                # 清理标题
                clean_title = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', title).strip()
                clean_title = re.sub(r'[-\s]+', '-', clean_title)
                filename = f"{domain}_{clean_title}"
            else:
                # 使用路径
                path = parsed_url.path.strip('/').replace('/', '_')
                filename = f"{domain}_{path}" if path else domain
            
            # 限制长度并清理
            filename = filename[:100].rstrip('-_')
            return filename or "webpage"
            
        except Exception as e:
            logger.warning(f"生成文件名失败: {str(e)}")
            return "webpage"
    
    def save_document(self, document_data: Dict[str, Any]) -> str:
        """保存解析的文档到01-parsed-docs目录"""
        try:
            metadata = document_data.get("metadata", {})
            filename = metadata.get("filename", "webpage")
            
            # 构建文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_format = metadata.get("parsing_config", {}).get("output_format", "markdown")
            output_filename = f"{filename}_trafilatura_{timestamp}.json"
            
            # 保存路径
            filepath = os.path.join("01-parsed-docs", output_filename)
            
            # 确保目录存在
            os.makedirs("01-parsed-docs", exist_ok=True)
            
            # 保存JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"文档已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存文档失败: {str(e)}")
            raise
    
    def batch_scrape(self, urls: List[str], delay: float = 1.0, 
                    max_workers: int = 4, **kwargs) -> List[Dict[str, Any]]:
        """
        批量抓取网页
        
        Args:
            urls: URL列表
            delay: 请求间隔（秒）
            max_workers: 最大并发数
            **kwargs: 传递给scrape_webpage的额外参数
            
        Returns:
            解析结果列表
        """
        results = []
        
        logger.info(f"开始批量抓取 {len(urls)} 个网页")
        
        for i, url in enumerate(urls):
            try:
                logger.info(f"处理URL {i+1}/{len(urls)}: {url}")
                result = self.scrape_webpage(url, **kwargs)
                results.append(result)
                
                # 添加延迟
                if i < len(urls) - 1 and delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"处理URL失败 {url}: {str(e)}")
                results.append(self._create_error_document(url, str(e)))
        
        logger.info(f"批量抓取完成，成功: {len([r for r in results if not r.get('metadata', {}).get('error')])}/{len(urls)}")
        return results
    
    def discover_feeds(self, homepage_url: str, target_lang: str = None) -> List[str]:
        """
        发现网站的RSS/Atom feeds
        
        Args:
            homepage_url: 网站首页URL
            target_lang: 目标语言 (例如: 'zh', 'en')
            
        Returns:
            发现的feed URL列表
        """
        try:
            feeds = find_feed_urls(homepage_url, target_lang=target_lang)
            logger.info(f"发现 {len(feeds)} 个feeds: {homepage_url}")
            return feeds
        except Exception as e:
            logger.error(f"发现feeds失败 {homepage_url}: {str(e)}")
            return []
    
    def discover_sitemap_urls(self, homepage_url: str, target_lang: str = None) -> List[str]:
        """
        从sitemap发现URL
        
        Args:
            homepage_url: 网站首页URL
            target_lang: 目标语言
            
        Returns:
            从sitemap发现的URL列表
        """
        try:
            urls = sitemap_search(homepage_url, target_lang=target_lang)
            logger.info(f"从sitemap发现 {len(urls)} 个URLs: {homepage_url}")
            return urls
        except Exception as e:
            logger.error(f"sitemap发现失败 {homepage_url}: {str(e)}")
            return []
    
    def focused_crawl(self, start_url: str, max_seen_urls: int = 100, 
                     max_known_urls: int = 10000) -> tuple:
        """
        执行聚焦爬虫
        
        Args:
            start_url: 起始URL
            max_seen_urls: 最大访问URL数
            max_known_urls: 最大已知URL数
            
        Returns:
            (待访问URLs, 已知URLs)
        """
        try:
            to_visit, known_urls = focused_crawler(
                start_url, 
                max_seen_urls=max_seen_urls,
                max_known_urls=max_known_urls
            )
            logger.info(f"聚焦爬虫完成: 待访问 {len(to_visit)}, 已知 {len(known_urls)}")
            return to_visit, known_urls
        except Exception as e:
            logger.error(f"聚焦爬虫失败 {start_url}: {str(e)}")
            return set(), set()
    
    def extract_with_fallback(self, url: str) -> Dict[str, Any]:
        """
        带备选方案的内容提取
        
        Args:
            url: 网页URL
            
        Returns:
            提取的内容数据
        """
        # 首先尝试 trafilatura
        if TRAFILATURA_AVAILABLE:
            try:
                return self.scrape_webpage(url)
            except Exception as e:
                logger.warning(f"trafilatura提取失败，尝试备选方案: {str(e)}")
        
        # 备选方案：简单的requests + BeautifulSoup
        if FALLBACK_AVAILABLE:
            try:
                return self._fallback_extraction(url)
            except Exception as e:
                logger.error(f"备选方案也失败: {str(e)}")
        
        # 最后返回错误文档
        return self._create_error_document(url, "所有提取方法都失败")
    
    def _fallback_extraction(self, url: str) -> Dict[str, Any]:
        """备选的简单提取方法"""
        logger.info(f"使用备选方案提取: {url}")
        
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 简单的内容提取
        title = soup.find('title')
        title_text = title.get_text().strip() if title else ""
        
        # 移除脚本和样式
        for script in soup(["script", "style"]):
            script.decompose()
        
        content = soup.get_text()
        
        return self._build_document_data(
            url=url,
            content=content,
            metadata={"title": title_text, "method": "fallback"},
            processing_time=0.0,
            extract_options={}
        )
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """获取提取统计信息"""
        return {
            "trafilatura_available": TRAFILATURA_AVAILABLE,
            "fallback_available": FALLBACK_AVAILABLE,
            "default_output_format": self.default_output_format,
            "target_language": self.target_language,
            "version_info": {
                "trafilatura": getattr(trafilatura, '__version__', 'unknown') if TRAFILATURA_AVAILABLE else None
            }
        } 