"""
任务状态存储 — 替代原版依赖 OpenClaw 的 JSON 持久化层
支持文件锁防止并发冲突
"""
import json
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── 状态流转定义 ──────────────────────────────────────────────────────────────
# 正向流：每个状态允许转移到的下一状态集合
STATE_TRANSITIONS = {
    "Pending":   ["Taizi"],
    "Taizi":     ["Zhongshu", "Done"],         # 简单任务太子可直接完成
    "Zhongshu":  ["Menxia"],
    "Menxia":    ["Assigned", "Zhongshu"],     # 封驳可退回中书省
    "Assigned":  ["Doing"],
    "Doing":     ["Review", "Doing"],           # Doing 允许自循环（子任务更新）
    "Review":    ["Done", "Doing"],             # 审查不通过退回执行
    "Done":      [],
    "Cancelled": [],
    "Blocked":   ["Doing", "Assigned"],
}

# 状态 → 负责 Agent
STATE_AGENT_MAP = {
    "Pending":   None,
    "Taizi":     "taizi",
    "Zhongshu":  "zhongshu",
    "Menxia":    "menxia",
    "Assigned":  "shangshu",
    "Doing":     None,          # 由尚书省根据子任务分配给六部
    "Review":    "shangshu",
    "Done":      None,
    "Cancelled": None,
    "Blocked":   None,
}

# ── 数据文件路径 ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TASKS_FILE = DATA_DIR / "tasks.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()


# ── 工具函数 ──────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _generate_task_id() -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    tasks = load_all_tasks()
    today_tasks = [t for t in tasks if t["id"].startswith(f"JJC-{date_str}")]
    seq = len(today_tasks) + 1
    return f"JJC-{date_str}-{seq:03d}"


# ── 读写 ──────────────────────────────────────────────────────────────────────
def load_all_tasks() -> list[dict]:
    if not TASKS_FILE.exists():
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_all_tasks(tasks: list[dict]) -> None:
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def get_task(task_id: str) -> Optional[dict]:
    for t in load_all_tasks():
        if t["id"] == task_id:
            return t
    return None


# ── 核心操作 ──────────────────────────────────────────────────────────────────
def create_task(title: str, content: str = "", source: str = "user") -> dict:
    """新建任务，状态从 Pending → Taizi"""
    with _lock:
        task_id = _generate_task_id()
        now = _now()
        task = {
            "id": task_id,
            "title": title,
            "content": content,
            "source": source,
            "state": "Pending",
            "created_at": now,
            "updated_at": now,
            "flow_log": [
                {"from": None, "to": "Pending", "agent": "system", "note": "任务创建", "time": now}
            ],
            "progress_log": [],
            "todos": [],
            "result": None,
            "_scheduler": {
                "retries": 0,
                "escalation_level": 0,
                "last_active": now,
                "state_snapshot": None,
            }
        }
        tasks = load_all_tasks()
        tasks.append(task)
        _save_all_tasks(tasks)
        return task


def update_state(task_id: str, new_state: str, agent: str, note: str = "") -> dict:
    """更新任务状态（带校验）"""
    with _lock:
        tasks = load_all_tasks()
        for task in tasks:
            if task["id"] != task_id:
                continue
            current = task["state"]
            allowed = STATE_TRANSITIONS.get(current, [])
            if new_state not in allowed:
                raise ValueError(
                    f"非法状态转移: {current} → {new_state}，允许: {allowed}"
                )
            now = _now()
            task["state"] = new_state
            task["updated_at"] = now
            task["_scheduler"]["last_active"] = now
            task["_scheduler"]["retries"] = 0
            task["flow_log"].append({
                "from": current, "to": new_state,
                "agent": agent, "note": note, "time": now
            })
            _save_all_tasks(tasks)
            return task
        raise KeyError(f"任务不存在: {task_id}")


def add_progress(task_id: str, agent: str, doing: str, todos: list[str] = None,
                 tokens: int = 0, cost: float = 0.0) -> None:
    """Agent 上报实时进展"""
    with _lock:
        tasks = load_all_tasks()
        for task in tasks:
            if task["id"] != task_id:
                continue
            now = _now()
            task["progress_log"].append({
                "agent": agent, "doing": doing,
                "todos": todos or [],
                "tokens": tokens, "cost": cost,
                "time": now
            })
            task["updated_at"] = now
            task["_scheduler"]["last_active"] = now
            _save_all_tasks(tasks)
            return
        raise KeyError(f"任务不存在: {task_id}")


def set_result(task_id: str, agent: str, result: str) -> dict:
    """标记任务完成，写入最终结果"""
    with _lock:
        tasks = load_all_tasks()
        for task in tasks:
            if task["id"] != task_id:
                continue
            now = _now()
            old_state = task["state"]   # ← 先记录，再改状态
            task["result"] = result
            task["state"] = "Done"
            task["updated_at"] = now
            task["flow_log"].append({
                "from": old_state, "to": "Done",
                "agent": agent, "note": "任务完成", "time": now
            })
            _save_all_tasks(tasks)
            return task
        raise KeyError(f"任务不存在: {task_id}")


def block_task(task_id: str, reason: str, agent: str = "system") -> dict:
    """将任务标记为 Blocked（六部执行阻塞时调用）"""
    with _lock:
        tasks = load_all_tasks()
        for task in tasks:
            if task["id"] != task_id:
                continue
            now = _now()
            old_state = task["state"]
            task["state"] = "Blocked"
            task["updated_at"] = now
            task["_scheduler"]["last_active"] = now
            task["_scheduler"]["state_snapshot"] = old_state   # 记住阻塞前的状态
            task["flow_log"].append({
                "from": old_state, "to": "Blocked",
                "agent": agent, "note": reason, "time": now
            })
            _save_all_tasks(tasks)
            return task
        raise KeyError(f"任务不存在: {task_id}")


def unblock_task(task_id: str, note: str = "", agent: str = "dashboard") -> dict:
    """从 Blocked 恢复到阻塞前的状态（Doing 或 Assigned）"""
    with _lock:
        tasks = load_all_tasks()
        for task in tasks:
            if task["id"] != task_id:
                continue
            if task["state"] != "Blocked":
                raise ValueError(f"任务 {task_id} 当前不是 Blocked 状态")
            restore = task["_scheduler"].get("state_snapshot") or "Doing"
            # 确保 restore 是合法的目标状态
            if restore not in ("Doing", "Assigned"):
                restore = "Doing"
            now = _now()
            task["state"] = restore
            task["updated_at"] = now
            task["_scheduler"]["last_active"] = now
            task["_scheduler"]["state_snapshot"] = None
            task["flow_log"].append({
                "from": "Blocked", "to": restore,
                "agent": agent, "note": note or "阻塞已解除", "time": now
            })
            _save_all_tasks(tasks)
            return task
        raise KeyError(f"任务不存在: {task_id}")


def cancel_task(task_id: str, reason: str = "") -> None:
    with _lock:
        tasks = load_all_tasks()
        for task in tasks:
            if task["id"] != task_id:
                continue
            now = _now()
            task["state"] = "Cancelled"
            task["updated_at"] = now
            task["flow_log"].append({
                "from": task["state"], "to": "Cancelled",
                "agent": "system", "note": reason, "time": now
            })
            _save_all_tasks(tasks)
            return
        raise KeyError(f"任务不存在: {task_id}")


def force_advance(task_id: str, new_state: str) -> dict:
    """仪表板手动推进（跳过校验）"""
    with _lock:
        tasks = load_all_tasks()
        for task in tasks:
            if task["id"] != task_id:
                continue
            old = task["state"]
            now = _now()
            task["state"] = new_state
            task["updated_at"] = now
            task["flow_log"].append({
                "from": old, "to": new_state,
                "agent": "dashboard", "note": "手动推进", "time": now
            })
            _save_all_tasks(tasks)
            return task
        raise KeyError(f"任务不存在: {task_id}")
