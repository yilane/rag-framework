import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from .config import config

def setup_logger(name='rag_system'):
    # 创建logs目录（如果不存在）
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), config.LOG_DIR)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件名（包含日期）
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'rag_system_{current_date}.log')

    # 创建logger
    logger = logging.getLogger(name)
    
    # 从配置文件获取日志级别
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # 创建 TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',  # 每天午夜切换到新文件
        interval=1,       # 间隔为1天
        backupCount=config.LOG_RETENTION_DAYS,   # 使用配置的保留天数
        encoding='utf-8'
    )

    # 设置日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # 清除现有的处理器（避免重复）
    logger.handlers.clear()
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 创建全局logger实例
logger = setup_logger() 