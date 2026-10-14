"""撤销栈：undo 记录的持久化管理（%APPDATA%/RenameKit/undo/）。

文件布局：{session_id}.json，一条会话一个文件。
栈深 10：push 时超出则删除最旧的 completed 记录。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from src.core.models import RenameSession
from src.utils.config import appdata_dir
from src.utils.logger import get_logger

logger = get_logger()

MAX_STACK = 10
# 可撤销状态：只有 completed 才能撤销；pending/undoing 是崩溃悬挂态
UNDOABLE = "completed"
SUSPENDED = ("pending", "undoing")


def undo_dir() -> Path:
    """undo 记录目录（不存在则创建）。"""
    d = appdata_dir() / "undo"
    d.mkdir(parents=True, exist_ok=True)
    return d


def push(session: RenameSession) -> None:
    """写入/更新一条记录，并把栈裁剪到 MAX_STACK。

    不用 tmp+rename 原子写：本机 AppData 下 os.rename 被火绒拦截
    （WinError 17），直接写目标；崩溃留半条 JSON 会被 load_all 跳过。
    """
    path = undo_dir() / f"{session.session_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
    _trim()


def discard(session_id: str) -> None:
    """删除一条记录（撤销成功 / 执行全回滚后调用）。"""
    (undo_dir() / f"{session_id}.json").unlink(missing_ok=True)


def load_all() -> list[RenameSession]:
    """按 timestamp 升序加载全部记录。"""
    sessions: list[RenameSession] = []
    for p in undo_dir().glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                sessions.append(RenameSession.from_dict(json.load(f)))
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.warning("undo 记录损坏，跳过 %s: %s", p.name, e)
    sessions.sort(key=lambda s: s.timestamp)
    return sessions


def load_latest_undoable() -> RenameSession | None:
    """最近一条 completed 记录（撤销按钮的目标）。"""
    for s in reversed(load_all()):
        if s.status == UNDOABLE:
            return s
    return None


def has_undoable() -> bool:
    return load_latest_undoable() is not None


def scan_suspended() -> list[RenameSession]:
    """扫描崩溃悬挂记录（pending/undoing），启动时提示用户。"""
    return [s for s in load_all() if s.status in SUSPENDED]


def involved_directories() -> list[str]:
    """全部记录涉及的目录（启动清理探测残留用）。"""
    dirs: set[str] = set()
    for s in load_all():
        for op in s.operations:
            d = os.path.dirname(op.orig)
            if d:
                dirs.add(d)
    return sorted(dirs)


def _trim() -> None:
    """栈深裁剪：超过 MAX_STACK 时删除最旧的 completed 记录。"""
    sessions = load_all()
    completed = [s for s in sessions if s.status in (UNDOABLE, "partial")]
    excess = len(completed) - MAX_STACK
    for s in completed[:max(excess, 0)]:
        discard(s.session_id)
        logger.info("undo 栈裁剪，移除最旧记录 %s", s.session_id[:8])


def new_session(operations) -> RenameSession:
    """创建 pending 状态的新会话。"""
    return RenameSession(
        session_id=os.urandom(16).hex(),
        timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
        status="pending",
        operations=list(operations),
    )
