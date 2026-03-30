"""
通用任务存储层 — 状态机由制度定义，不硬编码
"""
import json
import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# ── 数据文件路径 ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TASKS_FILE = DATA_DIR / "tasks.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()

# ── 默认状态机（三省六部制，向后兼容）──────────────────────────────────────────
DEFAULT_STATE_TRANSITIONS: Dict[str, List[str]] = {
    "Pending":   ["Taizi"],
    "Taizi":     ["Zhongshu", "Done"],
    "Zhongshu":  ["Menxia"],
    "Menxia":    ["Assigned", "Zhongshu"],
    "Assigned":  ["Doing"],
    "Doing":     ["Review", "Doing"],
    "Review":    ["Done", "Doing"],
    "Done":      [],
    "Cancelled": [],
    "Blocked":   ["Doing", "Assigned"],
}

DEFAULT_STATE_AGENT_MAP: Dict[str, Optional[str]] = {
    "Pending":   None,
    "Taizi":     "taizi",
    "Zhongshu":  "zhongshu",
    "Menxia":    "menxia",
    "Assigned":  "shangshu",
    "Doing":     None,
    "Review":    "shangshu",
    "Done":      None,
    "Cancelled": None,
    "Blocked":   None,
}

# 运行时状态机（可被制度覆盖）
_state_transitions: Dict[str, List[str]] = dict(DEFAULT_STATE_TRANSITIONS)
_state_agent_map: Dict[str, Optional[str]] = dict(DEFAULT_STATE_AGENT_MAP)


def configure_state_machine(
    transitions: Dict[str, List[str]],
    agent_map: Dict[str, Optional[str]],
):
    """
    由制度模块调用，配置该制度的状态机规则。
    必须在 dispatch() 开始前调用。
    """
    global _state_transitions, _state_agent_map
    _state_transitions = transitions
    _state_agent_map = agent_map


def get_state_transitions() -> Dict[str, List[str]]:
    """获取当前状态转移规则"""
    return dict(_state_transitions)


def get_state_agent_map() -> Dict[str, Optional[str]]:
    """获取当前状态-角色映射"""
    return dict(_state_agent_map)


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
def load_all_tasks() -> list:
    if not TASKS_FILE.exists():
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_all_tasks(tasks: list) -> None:
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def get_task(task_id: str) -> Optional[dict]:
    for t in load_all_tasks():
        if t["id"] == task_id:
            return t
    return None


# ── 核心操作 ──────────────────────────────────────────────────────────────────
def create_task(title: str, content: str = "", source: str = "user") -> dict:
    """新建任务，初始状态 Pending"""
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
            allowed = _state_transitions.get(current, [])
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


def add_progress(task_id: str, agent: str, doing: str, todos: list = None,
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
            old_state = task["state"]
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
    """将任务标记为 Blocked"""
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
            task["_scheduler"]["state_snapshot"] = old_state
            task["flow_log"].append({
                "from": old_state, "to": "Blocked",
                "agent": agent, "note": reason, "time": now
            })
            _save_all_tasks(tasks)
            return task
        raise KeyError(f"任务不存在: {task_id}")


def unblock_task(task_id: str, note: str = "", agent: str = "dashboard") -> dict:
    """从 Blocked 恢复到阻塞前的状态"""
    with _lock:
        tasks = load_all_tasks()
        for task in tasks:
            if task["id"] != task_id:
                continue
            if task["state"] != "Blocked":
                raise ValueError(f"任务 {task_id} 当前不是 Blocked 状态")
            restore = task["_scheduler"].get("state_snapshot") or "Doing"
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
