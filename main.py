#!/usr/bin/env python3
"""
三省六部 · 独立版入口
用法：
  python main.py                      # 启动 Dashboard（看板服务）
  python main.py run "你的旨意"        # 命令行直接运行一次流水线
  python main.py chat                  # 进入交互式命令行模式
"""
import sys
import os
from pathlib import Path

# 加载 .env
_env = Path(__file__).parent / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)
else:
    # 没有 .env 时从 .env.example 提示
    print("⚠️  未找到 .env，请复制 .env.example → .env 并填入 API Key")
    sys.exit(1)


def cmd_dashboard():
    """启动看板 Web 服务"""
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("DASHBOARD_PORT", 7891))
    from dashboard.server import run_server
    run_server(host, port)


def cmd_run(message: str):
    """一次性运行流水线，打印结果"""
    from scripts.orchestrator import run_pipeline

    def on_event(event_type, data):
        icons = {
            "taizi_start":   "👑",
            "taizi_done":    "✅",
            "zhongshu_start": "📜",
            "zhongshu_done": "✅",
            "menxia_start":  "⚖️",
            "menxia_done":   "✅",
            "shangshu_start": "📋",
            "done":          "🎉",
            "error":         "❌",
        }
        icon = icons.get(event_type, "  ")
        if event_type == "taizi_done":
            print(f"  {icon} 太子已接旨 → 任务 {data.get('task_id')}: {data.get('title')}")
        elif event_type == "menxia_done":
            v = "准奏✅" if data.get("verdict") == "approved" else "封驳❌"
            print(f"  {icon} 门下省审核: {v}  {data.get('reason','')[:60]}")
        elif event_type == "done":
            pass  # 最后统一打印结果
        elif event_type == "error":
            print(f"  {icon} 流程异常: {data.get('error')}")
        else:
            print(f"  {icon} [{event_type}]")

    print(f"\n🏛️  三省六部开始处理：\"{message}\"\n{'─'*50}")
    result = run_pipeline(message, on_event=on_event)
    print(f"\n{'─'*50}")
    if result.get("state") == "Done":
        print(f"🎉 任务完成 [{result.get('task_id')}]\n")
        print(result.get("result", ""))
    else:
        print(f"❌ 任务异常: {result.get('result')}")


def cmd_chat():
    """交互式命令行"""
    print("🏛️  三省六部 · 交互模式（输入 exit 退出）\n")
    while True:
        try:
            msg = input("皇上: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退朝！")
            break
        if msg.lower() in ("exit", "quit", "退出"):
            print("退朝！")
            break
        if not msg:
            continue
        cmd_run(msg)
        print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "dashboard":
        cmd_dashboard()
    elif args[0] == "run" and len(args) >= 2:
        cmd_run(" ".join(args[1:]))
    elif args[0] == "chat":
        cmd_chat()
    else:
        print(__doc__)
