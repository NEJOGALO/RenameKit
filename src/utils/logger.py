"""日志初始化：输出到 %APPDATA%/RenameKit/logs/renamkit.log。

滚动保留：单文件最大 512KB，保留 3 份备份，便于用户反馈 bug 时取证。
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from src.utils.config import appdata_dir

_LOGGER_NAME = "RenameKit"
_INITIALIZED = False


def setup_logger() -> logging.Logger:
    """初始化全局日志器（重复调用只初始化一次）。"""
    global _INITIALIZED
    logger = logging.getLogger(_LOGGER_NAME)
    if _INITIALIZED:
        return logger

    log_dir = appdata_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "renamkit.log",
        maxBytes=512 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    _INITIALIZED = True
    logger.info("RenameKit 启动，日志初始化完成")
    return logger


def get_logger() -> logging.Logger:
    """获取全局日志器（未初始化时自动初始化）。"""
    return setup_logger()
