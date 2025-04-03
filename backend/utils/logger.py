import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

def setup_logger(name='rag_system'):
    # 创建logs目录（如果不存在）
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件名（包含日期）
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'rag_system_{current_date}.log')

    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 创建 TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',  # 每天午夜切换到新文件
        interval=1,       # 间隔为1天
        backupCount=30,   # 保留30天的日志文件
        encoding='utf-8'
    )

    # 设置日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 创建全局logger实例
logger = setup_logger() 