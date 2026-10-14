"""文件操作工具：安全重命名与 Windows 属性辅助。"""

from __future__ import annotations

import ctypes
import os
import shutil

FILE_ATTRIBUTE_HIDDEN = 0x02


def safe_rename(src: str, dst: str, rename_preferred: bool = True) -> None:
    """把 src 重命名/移动到 dst。

    rename_preferred=True（默认）：先试 os.rename（同盘最快），失败回退
    复制+删除——绕过本机 AppData\\Roaming 下 os.rename 被火绒拦截的
    WinError 17，也天然处理跨盘符。
    rename_preferred=False：探测已知该目录 rename 不可用，直接走复制+删除，
    省去每文件一次注定失败的 rename 尝试。

    Raises:
        OSError: 两条路径都失败时抛出。
    """
    if os.path.exists(dst):
        raise FileExistsError(f"目标已存在: {dst}")
    if rename_preferred:
        try:
            os.rename(src, dst)
            return
        except OSError:
            pass
    # 回退：复制+删除。copy 成功但 remove 失败（如文件被占用）时，
    # 必须清掉 dst 半成品，保证失败后文件系统干净（src 原样保留）。
    try:
        shutil.copy2(src, dst)
        os.remove(src)
    except Exception:
        try:
            if os.path.exists(dst):
                os.remove(dst)
        except OSError:
            pass
        raise


def set_hidden(path: str) -> None:
    """设置文件隐藏属性（Windows），失败静默——隐藏只影响观感不影响正确性。"""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path, FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass
