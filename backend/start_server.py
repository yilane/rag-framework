#!/usr/bin/env python3
import subprocess
from utils.config import config

def main():
    # 从配置中获取host和port
    host = config.HOST
    port = config.PORT
    
    # 构建基本命令
    command = [
        'uvicorn',
        'main:app',
        '--reload',
        f'--host={host}',
        f'--port={port}'
    ]
    
    # 如果DEBUG为True，添加debug日志级别
    if config.DEBUG:
        command.append('--log-level=debug')
        print(f'正在启动服务器 - Host: {host}, Port: {port}, Debug模式')
    else:
        print(f'正在启动服务器 - Host: {host}, Port: {port}')
    
    # 执行命令
    try:
        subprocess.run(command)
    except KeyboardInterrupt:
        print('\n服务器已停止')
    except Exception as e:
        print(f'启动服务器时发生错误: {str(e)}')

if __name__ == '__main__':
    main() 