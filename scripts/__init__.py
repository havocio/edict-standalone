"""
scripts/__init__.py — 兼容层
将 framework.task_store 重导出为 scripts.task_store
"""
from framework import task_store

# 重导出所有公开接口，保持 scripts.task_store.xxx 兼容
__all__ = [
    "configure_state_machine",
    "get_state_transitions",
    "get_state_agent_map",
    "load_all_tasks",
    "get_task",
    "create_task",
    "update_state",
    "add_progress",
    "set_result",
    "block_task",
    "unblock_task",
    "cancel_task",
    "force_advance",
]
