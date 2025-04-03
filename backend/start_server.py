#!/usr/bin/env python3
import subprocess
import argparse
import os
import signal
import sys
import psutil
from utils.config import config

def get_pid_file():
    """获取PID文件路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.pid')

def save_pid(pid):
    """保存进程ID到文件"""
    with open(get_pid_file(), 'w') as f:
        f.write(str(pid))

def get_saved_pid():
    """从文件中读取进程ID"""
    try:
        with open(get_pid_file(), 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None

def find_uvicorn_process():
    """查找运行中的uvicorn进程"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'uvicorn' in proc.info['name'] and 'main:app' in ' '.join(proc.info['cmdline']):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def is_process_running(pid):
    """检查进程是否在运行"""
    try:
        return psutil.pid_exists(pid)
    except Exception:
        return False

def kill_process_tree(pid):
    """终止进程及其所有子进程"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # 先终止子进程
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        # 终止主进程
        parent.terminate()
        
        # 等待进程结束
        _, alive = psutil.wait_procs(children + [parent], timeout=3)
        
        # 如果有进程还在运行，强制结束
        for proc in alive:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
                
    except psutil.NoSuchProcess:
        pass

def start_server(args):
    """启动服务器"""
    # 检查服务是否已经在运行
    pid = get_saved_pid() or find_uvicorn_process()
    if pid and is_process_running(pid):
        print(f'服务已经在运行中 (PID: {pid})')
        return

    host = config.HOST
    port = config.PORT
    
    # 构建基本命令
    command = [
        'uvicorn',
        'main:app',
        '--reload' if not args.no_reload else '',
        f'--host={host}',
        f'--port={port}'
    ]
    
    # 如果DEBUG为True，添加debug日志级别
    if config.DEBUG:
        command.append('--log-level=debug')
        print(f'正在启动服务器 - Host: {host}, Port: {port}, Debug模式')
    else:
        print(f'正在启动服务器 - Host: {host}, Port: {port}')

    # 过滤掉空字符串
    command = [cmd for cmd in command if cmd]
    
    try:
        if args.daemon:
            print('服务器将在后台运行')
            # 使用 nohup 命令在后台运行
            full_command = f"nohup {' '.join(command)} > nohup.out 2>&1 &"
            subprocess.run(full_command, shell=True)
            
            # 等待一下确保进程启动
            import time
            time.sleep(2)
            
            # 获取新启动的进程ID
            pid = find_uvicorn_process()
            if pid:
                save_pid(pid)
                print(f'服务已启动 (PID: {pid})')
            else:
                print('服务启动可能失败，请检查 nohup.out 文件')
        else:
            process = subprocess.Popen(command)
            save_pid(process.pid)
            print(f'服务已启动 (PID: {process.pid})')
            process.wait()
    except KeyboardInterrupt:
        print('\n服务器已停止')
    except Exception as e:
        print(f'启动服务器时发生错误: {str(e)}')

def stop_server():
    """停止服务器"""
    # 首先尝试从PID文件获取进程ID
    pid = get_saved_pid()
    
    # 如果PID文件不存在，尝试查找运行中的uvicorn进程
    if not pid:
        pid = find_uvicorn_process()
        
    if not pid:
        print('未找到运行中的服务')
        return
    
    try:
        print(f'正在停止服务 (PID: {pid})...')
        kill_process_tree(pid)
        print('服务已停止')
        
        # 清理PID文件
        if os.path.exists(get_pid_file()):
            os.remove(get_pid_file())
            
    except Exception as e:
        print(f'停止服务时发生错误: {str(e)}')
        # 如果进程已经不存在，也要清理PID文件
        if os.path.exists(get_pid_file()):
            os.remove(get_pid_file())

def reload_server():
    """重启服务器"""
    print('正在重启服务...')
    stop_server()
    # 等待进程完全停止
    import time
    time.sleep(2)
    start_server(parse_args(['start']))

def parse_args(args=None):
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='RAG 服务管理脚本')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # start 命令
    start_parser = subparsers.add_parser('start', help='启动服务')
    start_parser.add_argument('-d', '--daemon', action='store_true', help='在后台运行服务')
    start_parser.add_argument('--no-reload', action='store_true', help='禁用自动重载')

    # stop 命令
    subparsers.add_parser('stop', help='停止服务')

    # reload 命令
    subparsers.add_parser('reload', help='重启服务')

    return parser.parse_args(args)

def main():
    args = parse_args()
    
    if args.command == 'start':
        start_server(args)
    elif args.command == 'stop':
        stop_server()
    elif args.command == 'reload':
        reload_server()
    else:
        # 默认行为：启动服务
        start_server(parse_args(['start']))

if __name__ == '__main__':
    main() 