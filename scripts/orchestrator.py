"""
scripts/orchestrator.py — 兼容层
委托给当前活跃的制度模块
"""
from logger import logger


def run_pipeline(user_message: str, on_event=None) -> dict:
    """
    兼容接口：委托给当前制度模块的 dispatch 方法
    """
    import framework.task_store as task_store
    from regimes import get_current_regime

    regime = get_current_regime()
    logger.info(f"使用制度: {regime.meta.name} ({regime.meta.id})")
    return regime.dispatch(user_message, task_store, on_event=on_event)
