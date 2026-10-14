"""配置读写：统一存放在 %APPDATA%/RenameKit/config.json。

放在应用数据目录而非项目目录，避免打包成 exe 后
安装在只读位置（如 Program Files）时写入失败。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# 默认配置
DEFAULT_CONFIG: dict[str, Any] = {
    "theme": "dark",       # 深色 / 浅色
    "first_run": True,     # 是否首次启动（阶段6 引导用）
}


def appdata_dir() -> Path:
    """返回 %APPDATA%/RenameKit 目录（不存在则创建）。"""
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / "RenameKit"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    """返回配置文件完整路径。"""
    return appdata_dir() / "config.json"


def load_config() -> dict[str, Any]:
    """读取配置文件；文件缺失或损坏时返回默认配置。"""
    path = config_path()
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                merged = dict(DEFAULT_CONFIG)
                merged.update(data)
                return merged
    except (json.JSONDecodeError, OSError):
        pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict[str, Any]) -> None:
    """写入配置文件，写失败时静默忽略（不阻断界面操作）。

    注意：不用 tmp+rename 原子替换——实测本机 os.replace/rename 会抛
    WinError 17（疑似安全软件拦截），直接写入更可靠。
    """
    try:
        path = config_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
