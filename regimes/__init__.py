"""
制度模块包 — 发现、注册、加载所有制度
"""
import os
from pathlib import Path
from typing import List
from logger import logger


# 已发现的制度模块 ID 列表
_discovered: List[str] = []


def _discover_regimes() -> List[str]:
    """
    扫描 regimes/ 目录，发现所有制度模块
    每个子目录包含 __init__.py 就被视为一个制度模块
    """
    global _discovered
    if _discovered:
        return _discovered
    
    regimes_dir = Path(__file__).parent
    if not regimes_dir.exists():
        return []
    
    for item in regimes_dir.iterdir():
        if item.is_dir() and (item / "__init__.py").exists():
            # 跳过私有目录（如 __pycache__）
            if not item.name.startswith("_") and item.name != "regimes":
                _discovered.append(item.name)
                logger.debug(f"发现制度模块: {item.name}")
    
    logger.info(f"已发现 {len(_discovered)} 个制度模块: {_discovered}")
    return _discovered


def _load_all_regimes() -> List[str]:
    """加载所有制度模块（导入时会触发注册）"""
    discovered = _discover_regimes()
    for regime_id in discovered:
        try:
            __import__(f"regimes.{regime_id}", level=0)
        except Exception as e:
            logger.warning(f"加载制度模块 {regime_id} 失败: {e}")
    return discovered


def get_available_regimes() -> List[str]:
    """返回所有可用的制度 ID"""
    return _discover_regimes()


def get_regime(regime_id: str):
    """获取指定制度的实例"""
    from framework.core import RegimeRegistry
    
    # 先加载所有（确保注册表完整）
    _load_all_regimes()
    
    return RegimeRegistry.get(regime_id)


def get_current_regime():
    """
    获取当前制度实例
    使用 framework.core 中的公共函数
    """
    from framework.core import get_current_regime as _get_current_regime
    return _get_current_regime()
