"""
统一日志配置模块

使用方法:
    from logger import logger
    logger.debug("调试信息")

    或者直接调用configure_logging()进行全局配置
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# 全局配置状态
_configured = False
_log_file: Optional[Path] = None

# ==================== 统一的logger实例 ====================
# 所有模块使用同一个logger实例，避免因__name__不同导致的不同logger
logger = logging.getLogger("edict")
# =========================================================


def configure_logging(
    log_file: Optional[Path] = None,
    level: int = logging.DEBUG,
    console_output: bool = True,
    format_str: Optional[str] = None
) -> None:
    """
    配置全局日志系统

    Args:
        log_file: 日志文件路径，如果为None则使用默认的dashboard.log
        level: 日志级别，默认DEBUG
        console_output: 是否输出到控制台
        format_str: 自定义日志格式，如果为None则使用默认格式
    """
    global _configured, _log_file

    if _configured:
        return

    # 确定日志文件路径
    if log_file is None:
        ROOT = Path(__file__).parent
        _log_file = ROOT / "dashboard.log"
    else:
        _log_file = log_file

    # 默认格式
    if format_str is None:
        format_str = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

    # 配置handlers
    handlers = []

    # 文件handler
    file_handler = logging.FileHandler(_log_file, encoding="utf-8")
    file_handler.setLevel(level)
    handlers.append(file_handler)

    # 控制台handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        handlers.append(console_handler)

    # 全局配置
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=handlers,
        force=True  # 强制重新配置
    )

    # 显式设置统一logger的日志级别
    logger.setLevel(level)

    _configured = True

    logger.info(f"日志系统已初始化: file={_log_file}, level={logging.getLevelName(level)}")


def get_log_file() -> Optional[Path]:
    """获取当前日志文件路径"""
    return _log_file


# 模块导入时自动配置（可选）
# 如果想延迟配置，可以注释掉下面这行
# configure_logging()
