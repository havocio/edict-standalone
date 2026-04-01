#!/usr/bin/env python3
"""
Edict — 可插拔制度多 Agent 编排系统
用法：
  python main.py                               # 启动 Dashboard
  python main.py run "你的旨意"                 # 命令行运行一次
  python main.py chat                           # 交互式命令行
  python main.py run "任务" --regime democratic_centralism  # 指定制度运行
"""
import sys
import os
from pathlib import Path
from framework.core import set_current_regime, get_current_regime_id

# 加载 .env
_env = Path(__file__).parent / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)
else:
    print("⚠️  未找到 .env，请复制 .env.example → .env 并填入 API Key")
    sys.exit(1)


def _get_regime_name() -> str:
    """获取当前制度名称（用于显示）"""
    from framework.core import get_current_regime
    try:
        return get_current_regime().meta.name
    except Exception:
        return get_current_regime_id()


def cmd_dashboard():
    """启动看板 Web 服务"""
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("DASHBOARD_PORT", 7891))
    from dashboard_server import start_dashboard_server
    start_dashboard_server(port)


def process_message(message: str, on_event=None) -> dict:
    """处理消息（供外部调用）"""
    from scripts.orchestrator import run_pipeline
    return run_pipeline(message, on_event=on_event)


def cmd_run(message: str, regime_override: str = None):
    """一次性运行流水线，打印结果"""
    # 如果命令行指定了制度，临时覆盖
    if regime_override:
        set_current_regime(regime_override)

    regime_name = _get_regime_name()

    def on_event(event_type, data):
        icons = {
            "taizi_start": "👑", "taizi_done": "✅",
            "secretary_start": "📋", "secretary_done": "✅",
            "zhongshu_start": "📜", "zhongshu_done": "✅",
            "menxia_start": "⚖️", "menxia_done": "✅",
            "congress_start": "🏛️", "congress_done": "✅",
            "committee_start": "🎯", "committee_done": "✅",
            "shangshu_start": "📋",
            "executor_start": "⚙️",
            "review_start": "🔍", "audit_start": "📊",
            "done": "🎉", "error": "❌",
        }
        icon = icons.get(event_type, "  ")
        if event_type in ("taizi_done", "secretary_done"):
            print(f"  {icon} 接收提案 → 任务 {data.get('task_id')}: {data.get('title')}")
        elif event_type == "menxia_done":
            v = "准奏✅" if data.get("verdict") == "approved" else "封驳❌"
            print(f"  {icon} 门下省审核: {v}  {data.get('reason','')[:60]}")
        elif event_type == "congress_done":
            print(f"  {icon} 议会共识: {data.get('consensus','')[:60]}...")
        elif event_type == "committee_done":
            print(f"  {icon} 常委会决策: {data.get('decision','')[:60]}...")
        elif event_type == "done":
            pass
        elif event_type == "error":
            print(f"  {icon} 流程异常: {data.get('error')}")
        else:
            print(f"  {icon} [{event_type}]")

    print(f"\n🏛️  [{regime_name}] 开始处理：\"{message}\"\n{'─'*50}")
    result = process_message(message, on_event=on_event)
    print(f"\n{'─'*50}")
    if result.get("state") == "Done":
        print(f"🎉 任务完成 [{result.get('task_id')}]\n")
        print(result.get("result", ""))
    else:
        print(f"❌ 任务异常: {result.get('result')}")


def cmd_chat(regime_override: str = None):
    """交互式命令行"""
    if regime_override:
        set_current_regime(regime_override)
    regime_name = _get_regime_name()
    print(f"🏛️  [{regime_name}] · 交互模式（输入 exit 退出）\n")
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


def _list_regimes():
    """列出所有可用制度"""
    from framework.core import RegimeRegistry
    from regimes import _load_all_regimes
    _load_all_regimes()
    metas = RegimeRegistry.list_all()
    if not metas:
        print("暂无可用制度")
        return
    print(f"\n{'═'*50}")
    print(f"  可用制度（共 {len(metas)} 个）")
    print(f"{'═'*50}")
    for m in metas:
        print(f"\n  {m.icon if hasattr(m, 'icon') else '🏛️'} {m.name} ({m.id})")
        print(f"     朝代: {m.era}")
        print(f"     标签: {', '.join(m.tags)}")
        print(f"     描述: {m.description[:60]}...")
    print(f"\n  当前默认: {get_current_regime_id()}")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "dashboard":
        cmd_dashboard()
    elif args[0] == "run" and len(args) >= 2:
        # 支持 --regime 参数
        regime = None
        msg_parts = []
        i = 1
        while i < len(args):
            if args[i] == "--regime" and i + 1 < len(args):
                regime = args[i + 1]
                i += 2
            else:
                msg_parts.append(args[i])
                i += 1
        if msg_parts:
            cmd_run(" ".join(msg_parts), regime_override=regime)
        else:
            print("用法: python main.py run \"你的旨意\" [--regime 制度ID]")
    elif args[0] == "chat":
        regime = None
        if "--regime" in args:
            idx = args.index("--regime")
            if idx + 1 < len(args):
                regime = args[idx + 1]
        cmd_chat(regime_override=regime)
    elif args[0] == "regimes":
        _list_regimes()
    else:
        print(__doc__)
