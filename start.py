#!/usr/bin/env python3
"""
一键启动脚本 - 同时启动后端 API 和前端开发服务器
用法: python start.py [--build]
  --build  先构建前端，再启动后端（生产模式）
"""
import subprocess
import sys
import time
import signal
import os
from pathlib import Path

ROOT = Path(__file__).parent

def run_backend():
    """启动后端服务"""
    print("[START] 启动后端服务...")
    return subprocess.Popen(
        [sys.executable, "dashboard_server.py"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

def run_frontend_dev():
    """启动前端开发服务器"""
    print("[START] 启动前端开发服务器...")
    return subprocess.Popen(
        "npm run dev",
        cwd=ROOT / "dashboard-ui",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=True
    )

def build_frontend():
    """构建前端"""
    print("[BUILD] 构建前端...")
    result = subprocess.run(
        "npm run build",
        cwd=ROOT / "dashboard-ui",
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=True
    )
    if result.returncode != 0:
        print("[ERROR] 前端构建失败:")
        print(result.stdout)
        print(result.stderr)
        return False
    print("[OK] 前端构建完成")
    return True

def stream_output(proc, prefix):
    """实时输出子进程日志"""
    for line in proc.stdout:
        print(f"[{prefix}] {line.rstrip()}")

def main():
    backend_proc = None
    frontend_proc = None

    def cleanup(signum=None, frame=None):
        """清理进程"""
        print("\n[STOP] 正在停止服务...")
        if frontend_proc:
            frontend_proc.terminate()
            frontend_proc.wait()
        if backend_proc:
            backend_proc.terminate()
            backend_proc.wait()
        print("[OK] 已停止")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # 检查是否需要构建
    if "--build" in sys.argv:
        if not build_frontend():
            sys.exit(1)
        # 生产模式：只启动后端
        backend_proc = run_backend()
        print("\n[OK] 服务已启动")
        print("[URL] 访问 http://127.0.0.1:7891")
        print("[TIP] 按 Ctrl+C 停止\n")
        stream_output(backend_proc, "后端")
    else:
        # 开发模式：同时启动前后端
        backend_proc = run_backend()
        time.sleep(3)  # 等后端先启动
        frontend_proc = run_frontend_dev()

        print("\n[OK] 服务已启动")
        print("[URL] 前端开发服务器 http://127.0.0.1:5173")
        print("[URL] 后端 API http://127.0.0.1:7891")
        print("[TIP] 按 Ctrl+C 停止\n")

        # 同时输出前后端日志
        import threading
        t1 = threading.Thread(target=stream_output, args=(backend_proc, "后端"), daemon=True)
        t2 = threading.Thread(target=stream_output, args=(frontend_proc, "前端"), daemon=True)
        t1.start()
        t2.start()

        # 等待任意进程结束
        while True:
            if backend_proc.poll() is not None:
                print("[ERROR] 后端进程退出")
                break
            if frontend_proc.poll() is not None:
                print("[ERROR] 前端进程退出")
                break
            time.sleep(0.5)

        cleanup()

if __name__ == "__main__":
    main()
